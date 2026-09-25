#include <dlfcn.h>

#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "rime_api.h"

namespace {

std::string sanitize(const char* text) {
  std::string result = text ? text : "";
  for (char& ch : result) {
    if (ch == '\t' || ch == '\n' || ch == '\r') {
      ch = ' ';
    }
  }
  return result;
}

void print_state(RimeApi* api, RimeSessionId session, const char* label) {
  RIME_STRUCT(RimeContext, context);
  if (!api->get_context(session, &context)) {
    std::cout << "STATE\t" << label << "\t\t0\n";
    return;
  }

  std::cout << "STATE\t" << label << '\t' << sanitize(context.composition.preedit) << '\t'
            << context.menu.num_candidates << '\t'
            << sanitize(context.commit_text_preview) << '\n';
  for (int i = 0; i < context.menu.num_candidates; ++i) {
    const auto& candidate = context.menu.candidates[i];
    std::cout << "CAND\t" << label << '\t' << i << '\t' << sanitize(candidate.text) << '\t'
              << sanitize(candidate.comment) << '\n';
  }
  api->free_context(&context);
}

// Press the select key for the first menu candidate whose text equals
// `wanted` (alternative_select_keys = "asdfghjkl;"). Returns false when the
// candidate is absent, so scenarios fail loudly instead of picking the wrong
// word when toneless ordering shifts.
bool select_candidate_by_text(RimeApi* api, RimeSessionId session, const char* wanted) {
  RIME_STRUCT(RimeContext, context);
  if (!api->get_context(session, &context)) return false;
  static const char kSelectKeys[] = "asdfghjkl;";
  for (int i = 0; i < context.menu.num_candidates; ++i) {
    if (std::string(context.menu.candidates[i].text) == wanted && i < 10) {
      api->free_context(&context);
      api->simulate_key_sequence(session, std::string(1, kSelectKeys[i]).c_str());
      return true;
    }
  }
  api->free_context(&context);
  return false;
}

// Move the menu highlight onto the first candidate whose text equals
// `wanted` by pressing Down, without committing (for keys that act on the
// highlighted candidate, e.g. the 手動漢羅 backslash mark).
bool highlight_candidate_by_text(RimeApi* api, RimeSessionId session, const char* wanted) {
  RIME_STRUCT(RimeContext, context);
  if (!api->get_context(session, &context)) return false;
  int idx = -1;
  for (int i = 0; i < context.menu.num_candidates; ++i) {
    if (std::string(context.menu.candidates[i].text) == wanted) {
      idx = i;
      break;
    }
  }
  api->free_context(&context);
  if (idx < 0) return false;
  for (int i = 0; i < idx; ++i) {
    api->process_key(session, 0xFF54, 0);  // Down
  }
  return true;
}

// One sentence-corpus row: label<TAB>hanzi<TAB>keys.
struct CorpusRow {
  std::string label;
  std::string hanzi;
  std::string keys;
};

bool read_corpus_tsv(const char* path, std::vector<CorpusRow>* rows) {
  std::ifstream in(path);
  if (!in) return false;
  std::string line;
  while (std::getline(in, line)) {
    if (!line.empty() && line.back() == '\r') line.pop_back();
    if (line.empty() || line[0] == '#') continue;
    const auto first = line.find('\t');
    if (first == std::string::npos) return false;
    const auto second = line.find('\t', first + 1);
    if (second == std::string::npos) return false;
    rows->push_back({line.substr(0, first), line.substr(first + 1, second - first - 1),
                     line.substr(second + 1)});
  }
  return !rows->empty();
}

// Sentence-accuracy harness (optional CORPUS_TSV argument): replay every row
// through (a) 漢羅 mode, dumping the whole-sentence candidate menu, and
// (b) 全羅 mode, committing the sentence and printing its word-boundary text.
int run_corpus(RimeApi* api, RimeSessionId session, const char* path) {
  std::vector<CorpusRow> rows;
  if (!read_corpus_tsv(path, &rows)) {
    std::cerr << "cannot read corpus rows from " << path << '\n';
    return 2;
  }
  for (const CorpusRow& row : rows) {
    api->simulate_key_sequence(session, row.keys.c_str());
    print_state(api, session, row.label.c_str());
    api->clear_composition(session);

    api->set_option(session, "full_romanization", true);
    api->simulate_key_sequence(session, (row.keys + " ").c_str());
    RIME_STRUCT(RimeCommit, commit);
    if (api->get_commit(session, &commit)) {
      std::cout << "COMMIT\t" << row.label << '\t' << sanitize(commit.text) << '\n';
      api->free_commit(&commit);
    } else {
      std::cout << "COMMIT\t" << row.label << "\t\n";
    }
    api->set_option(session, "full_romanization", false);
    api->clear_composition(session);
  }
  return 0;
}

}  // namespace

int main(int argc, char* argv[]) {
  if (argc != 4 && argc != 5) {
    std::cerr << "usage: rime_smoke LUA_PLUGIN SHARED_DATA USER_DATA [CORPUS_TSV]\n";
    return 2;
  }

  void* lua = dlopen(argv[1], RTLD_NOW | RTLD_GLOBAL);
  if (!lua) {
    std::cerr << "cannot load librime-lua: " << dlerror() << '\n';
    return 2;
  }

  RimeApi* api = rime_get_api();
  const char* modules[] = {"default", "lua", nullptr};
  RIME_STRUCT(RimeTraits, traits);
  const std::string build_dir = std::string(argv[3]) + "/build";
  traits.shared_data_dir = argv[2];
  traits.user_data_dir = argv[3];
  traits.prebuilt_data_dir = build_dir.c_str();
  traits.staging_dir = build_dir.c_str();
  traits.distribution_name = "Phah Tai-bun Test";
  traits.distribution_code_name = "phah_taibun_test";
  traits.distribution_version = "1";
  traits.app_name = "phah_taibun.test";
  traits.modules = modules;
  traits.log_dir = "";
  traits.min_log_level = 3;

  api->setup(&traits);
  api->initialize(&traits);
  const RimeSessionId session = api->create_session();
  if (!session || !api->select_schema(session, "phah_taibun")) {
    std::cerr << "cannot create a phah_taibun session\n";
    api->finalize();
    return 1;
  }

  if (argc == 5) {
    const int status = run_corpus(api, session, argv[4]);
    api->destroy_session(session);
    api->finalize();
    dlclose(lua);
    return status;
  }

  api->simulate_key_sequence(session, "`");
  print_state(api, session, "backtick");
  api->clear_composition(session);

  // 注音反查 (華→台): ~ + ㄔ (standard layout 't') surfaces Mandarin chars
  // annotated with Taiwanese readings. Space (NOT Tab — that only confirms
  // the Mandarin segment) hits phah_taibun_commit's reverse feed-back: the
  // highlighted char's TL reading is pushed back as main input.
  api->simulate_key_sequence(session, "~t");
  print_state(api, session, "reverse_zhuyin_t");
  api->process_key(session, 0x20, 0);  // Space: reverse feed-back
  print_state(api, session, "reverse_zhuyin_fed");
  api->clear_composition(session);

  // Symbol categories (rime-liur port): ` opens a directory, `NN jumps
  // straight into one of the 50 categories.
  api->simulate_key_sequence(session, "`");
  print_state(api, session, "backtick_menu");
  api->simulate_key_sequence(session, "25");
  print_state(api, session, "symbols_cat25");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "`01");
  print_state(api, session, "symbols_cat01");
  api->clear_composition(session);

  // Emoji browsing: `e opens the Unicode-group directory, `e1 picks a group.
  api->simulate_key_sequence(session, "`e");
  print_state(api, session, "emoji_menu");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "`e1");
  print_state(api, session, "emoji_group1");
  api->clear_composition(session);
  // Browse into the People & Body list and verify a skin-tone glyph beyond
  // its first page survives the real librime candidate path.
  api->simulate_key_sequence(session, "`e2");
  for (int page = 0; page < 16; ++page) {
    api->process_key(session, 0xFF56, 0);  // Page_Down
  }
  print_state(api, session, "emoji_group2_skin_tone");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "vvh");
  print_state(api, session, "help");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "tsiah8");
  print_state(api, session, "tsiah8");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "tai5-uan5");
  print_state(api, session, "known_hyphen");
  api->clear_composition(session);


  // Long-word-first invariant (PLAN section 9-1A): a dictionary word's
  // reading must surface the whole word, ranked above fragment candidates.
  api->simulate_key_sequence(session, "tsiah8-png7");
  print_state(api, session, "long_word");
  api->clear_composition(session);


  // Hot-char no-hijack (PLAN section 9-1C): high-frequency single
  // characters (我 gua2) must not fragment a dictionary word (食飯).
  api->simulate_key_sequence(session, "gua2-tsiah8-png7");
  print_state(api, session, "hot_char_word");
  api->clear_composition(session);


  // Slot-0 verbatim candidate (PLAN section 9-1E): invalid pinyin must
  // offer the raw input itself as the first candidate.
  api->simulate_key_sequence(session, "xqzv");
  print_state(api, session, "invalid_input");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "kio-tiann");
  print_state(api, session, "ood_hyphen");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "kiotiann");
  print_state(api, session, "ood_concat");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "tshui-sit");
  print_state(api, session, "ood_compose");
  api->clear_composition(session);

  // Word-by-word journey for an out-of-dictionary phrase (kio-tiann -> 橋鼎):
  // pick the word (= tone) per syllable via Tab selection mode, then commit.
  api->simulate_key_sequence(session, "kio");
  api->process_key(session, 0xFF09, 0);  // Tab: enter selection mode
  select_candidate_by_text(api, session, "\xe6\xa9\x8b");  // 橋
  api->simulate_key_sequence(session, "tiann");
  print_state(api, session, "word_by_word_mid");
  api->process_key(session, 0xFF09, 0);
  select_candidate_by_text(api, session, "\xe9\xbc\x8e");  // 鼎
  api->simulate_key_sequence(session, " ");  // confirm and commit
  RIME_STRUCT(RimeCommit, commit);
  if (api->get_commit(session, &commit)) {
    std::cout << "COMMIT\tword_by_word\t" << sanitize(commit.text) << '\n';
    api->free_commit(&commit);
  } else {
    std::cout << "COMMIT\tword_by_word\t\n";
  }
  api->clear_composition(session);

  api->simulate_key_sequence(session, "tsiah8 ");
  api->simulate_key_sequence(session, "qxyz");
  print_state(api, session, "origin_after_commit");
  api->clear_composition(session);

  // Punctuation during composition (rime-liur style, real keycodes).
  // Comma cascades the top candidate plus full-width ，(works today; the
  // preset binds comma→Page_Up only when already paging).
  api->simulate_key_sequence(session, "tsiah8");
  api->process_key(session, 0x2c, 0);  // comma
  {
    RIME_STRUCT(RimeCommit, punct_commit);
    if (api->get_commit(session, &punct_commit)) {
      std::cout << "COMMIT\thanlo_word_comma\t" << sanitize(punct_commit.text) << '\n';
      api->free_commit(&punct_commit);
    } else {
      std::cout << "COMMIT\thanlo_word_comma\t\n";
    }
    api->clear_composition(session);
  }

  // Period must cascade the word plus full-width 。(the default preset binds
  // period→Page_Down whenever a menu is open, swallowing the key).
  api->simulate_key_sequence(session, "tsiah8");
  api->process_key(session, 0x2e, 0);  // period
  {
    RIME_STRUCT(RimeCommit, period_commit);
    if (api->get_commit(session, &period_commit)) {
      std::cout << "COMMIT\thanlo_word_period\t" << sanitize(period_commit.text) << '\n';
      api->free_commit(&period_commit);
    } else {
      std::cout << "COMMIT\thanlo_word_period\t\n";
    }
    api->clear_composition(session);
  }

  // 全羅 mode: period must commit the romanization plus half-width period.
  // A throwaway Space commit first consumes sentence-position capitalization
  // so the commit text below is exact regardless of scenario order.
  api->set_option(session, "full_romanization", true);
  api->simulate_key_sequence(session, "tsiah8 ");
  {
    RIME_STRUCT(RimeCommit, warm_commit);
    if (api->get_commit(session, &warm_commit)) api->free_commit(&warm_commit);
  }
  api->simulate_key_sequence(session, "tsiah8");
  api->process_key(session, 0x2e, 0);  // period
  {
    RIME_STRUCT(RimeCommit, roman_period_commit);
    if (api->get_commit(session, &roman_period_commit)) {
      std::cout << "COMMIT\tfullroman_word_period\t" << sanitize(roman_period_commit.text) << '\n';
      api->free_commit(&roman_period_commit);
    } else {
      std::cout << "COMMIT\tfullroman_word_period\t\n";
    }
    api->clear_composition(session);
  }
  api->set_option(session, "full_romanization", false);

  // Auto-commit punctuation (liur-style): unambiguous marks commit directly
  // with the word. 漢羅 → full-width; quotes alternate “ ” per press.
  api->simulate_key_sequence(session, "tsiah8");
  api->process_key(session, 0x28, 0);  // ( → （
  {
    RIME_STRUCT(RimeCommit, lparen_commit);
    if (api->get_commit(session, &lparen_commit)) {
      std::cout << "COMMIT\thanlo_word_lparen\t" << sanitize(lparen_commit.text) << '\n';
      api->free_commit(&lparen_commit);
    } else {
      std::cout << "COMMIT\thanlo_word_lparen\t\n";
    }
    api->clear_composition(session);
  }

  api->simulate_key_sequence(session, "tsiah8");
  api->process_key(session, 0x2f, 0);  // / → 、
  {
    RIME_STRUCT(RimeCommit, slash_commit);
    if (api->get_commit(session, &slash_commit)) {
      std::cout << "COMMIT\thanlo_word_slash\t" << sanitize(slash_commit.text) << '\n';
      api->free_commit(&slash_commit);
    } else {
      std::cout << "COMMIT\thanlo_word_slash\t\n";
    }
    api->clear_composition(session);
  }

  api->simulate_key_sequence(session, "tsiah8");
  api->process_key(session, 0x3c, 0);  // < → 《
  {
    RIME_STRUCT(RimeCommit, angle_commit);
    if (api->get_commit(session, &angle_commit)) {
      std::cout << "COMMIT\thanlo_word_angle\t" << sanitize(angle_commit.text) << '\n';
      api->free_commit(&angle_commit);
    } else {
      std::cout << "COMMIT\thanlo_word_angle\t\n";
    }
    api->clear_composition(session);
  }

  // Empty composition: direct full-width commit, no confirm keystroke.
  api->process_key(session, 0x5f, 0);  // _ → ——
  {
    RIME_STRUCT(RimeCommit, underscore_commit);
    if (api->get_commit(session, &underscore_commit)) {
      std::cout << "COMMIT\thanlo_empty_underscore\t" << sanitize(underscore_commit.text) << '\n';
      api->free_commit(&underscore_commit);
    } else {
      std::cout << "COMMIT\thanlo_empty_underscore\t\n";
    }
    api->clear_composition(session);
  }

  // Double quote: first press “, second press ” (alternating, one per press).
  api->process_key(session, 0x22, 0);
  {
    RIME_STRUCT(RimeCommit, quote_open_commit);
    if (api->get_commit(session, &quote_open_commit)) {
      std::cout << "COMMIT\thanlo_quote_first\t" << sanitize(quote_open_commit.text) << '\n';
      api->free_commit(&quote_open_commit);
    } else {
      std::cout << "COMMIT\thanlo_quote_first\t\n";
    }
    api->clear_composition(session);
  }
  api->process_key(session, 0x22, 0);
  {
    RIME_STRUCT(RimeCommit, quote_close_commit);
    if (api->get_commit(session, &quote_close_commit)) {
      std::cout << "COMMIT\thanlo_quote_second\t" << sanitize(quote_close_commit.text) << '\n';
      api->free_commit(&quote_close_commit);
    } else {
      std::cout << "COMMIT\thanlo_quote_second\t\n";
    }
    api->clear_composition(session);
  }

  // 全羅 mode: the same keys stay half-width (slash → "/").
  api->set_option(session, "full_romanization", true);
  api->simulate_key_sequence(session, "tsiah8 ");
  {
    RIME_STRUCT(RimeCommit, warm2_commit);
    if (api->get_commit(session, &warm2_commit)) api->free_commit(&warm2_commit);
  }
  api->simulate_key_sequence(session, "tsiah8");
  api->process_key(session, 0x2f, 0);
  {
    RIME_STRUCT(RimeCommit, roman_slash_commit);
    if (api->get_commit(session, &roman_slash_commit)) {
      std::cout << "COMMIT\tfullroman_word_slash\t" << sanitize(roman_slash_commit.text) << '\n';
      api->free_commit(&roman_slash_commit);
    } else {
      std::cout << "COMMIT\tfullroman_word_slash\t\n";
    }
    api->clear_composition(session);
  }
  api->set_option(session, "full_romanization", false);

  // Emoji conversion (rime-emoji, default on): 一 gets 1️⃣ appended.
  api->simulate_key_sequence(session, "tsit8");
  print_state(api, session, "emoji_on");
  api->clear_composition(session);
  // The built-in Taiwan mapping must also surface on the matching place name.
  api->simulate_key_sequence(session, "tai5-uan5");
  print_state(api, session, "emoji_taiwan");
  api->clear_composition(session);

  api->set_option(session, "emoji_conversion", false);
  api->simulate_key_sequence(session, "tsit8");
  print_state(api, session, "emoji_off");
  api->clear_composition(session);
  api->set_option(session, "emoji_conversion", true);

  // 漢羅混用 candidate (latin + hanzi mixed, e.g. á無) keeps full-width 。
  api->simulate_key_sequence(session, "a2-bo5");
  api->process_key(session, 0x2e, 0);  // period
  {
    RIME_STRUCT(RimeCommit, mixed_period_commit);
    if (api->get_commit(session, &mixed_period_commit)) {
      std::cout << "COMMIT\thanlo_mixed_word_period\t" << sanitize(mixed_period_commit.text) << '\n';
      api->free_commit(&mixed_period_commit);
    } else {
      std::cout << "COMMIT\thanlo_mixed_word_period\t\n";
    }
    api->clear_composition(session);
  }


  // 拍台文(Telex): tone letters (d=5, w=7, y=3, v=2/8, q=9), z→ts, zh→tsh,
  // f = syllable hyphen. The Lua processor normalizes input to numeric TL
  // keys before the speller, so dictionary/user-dict stay canonical.
  if (!api->select_schema(session, "phah_taibun_telex")) {
    std::cerr << "cannot select phah_taibun_telex\n";
    api->finalize();
    return 1;
  }

  api->simulate_key_sequence(session, "taid");
  print_state(api, session, "telex_taid");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "giv");
  print_state(api, session, "telex_giv");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "taidfgiv");
  print_state(api, session, "telex_taidfgiv");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "ziahv");
  print_state(api, session, "telex_ziahv");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "zhiahv");
  print_state(api, session, "telex_zhiahv");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "tngyflaid");
  print_state(api, session, "telex_tngyflaid");
  api->clear_composition(session);

  // Digitless POJ in the Telex schema is a documented limitation (the
  // toneless boost filter is main-schema only); toned POJ works.
  api->simulate_key_sequence(session, "chhia1");
  print_state(api, session, "telex_chhia1");
  api->clear_composition(session);

  // Telex schema: period must also cascade word + full-width 。
  api->simulate_key_sequence(session, "ziahv");
  api->process_key(session, 0x2e, 0);  // period
  {
    RIME_STRUCT(RimeCommit, telex_period_commit);
    if (api->get_commit(session, &telex_period_commit)) {
      std::cout << "COMMIT\ttelex_word_period\t" << sanitize(telex_period_commit.text) << '\n';
      api->free_commit(&telex_period_commit);
    } else {
      std::cout << "COMMIT\ttelex_word_period\t\n";
    }
    api->clear_composition(session);
  }

  // Main schema isolation: "taid" must NOT become tai5 there.
  if (!api->select_schema(session, "phah_taibun")) {
    std::cerr << "cannot select phah_taibun\n";
    api->finalize();
    return 1;
  }
  api->simulate_key_sequence(session, "taid");
  print_state(api, session, "main_taid");
  api->clear_composition(session);

  // Han-lo copy shown on the landing page (docs/index.html) must be
  // typeable with the IME itself; tests/test_landing_hanlo.py pins the
  // visible text to these engine states.
  api->simulate_key_sequence(session, "peh8-ue7-ji7");
  print_state(api, session, "hanlo_poj");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "tai5-gi2");
  print_state(api, session, "hanlo_taigi");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "e7-hiau2-kong2-tai5-gi2");
  print_state(api, session, "hanlo_sentence");
  api->clear_composition(session);

  // === 連打 (continuous whole-sentence typing, v0.8.0) ===
  // Article: funbiochampion.com 是按怎人退酒了後定定會袂記得啉酒醉的時所做的代誌
  api->simulate_key_sequence(session,
      "si7-an2-tsuann2-lang5-the3-tsiu2-liau2-au7-tiann7-tiann7-e7-be7-ki3-"
      "tsit8-lim1-tsiu2-tsui3-e5-si5-soo2-tso3-e5-tai7-tsi3");
  print_state(api, session, "liantua_example");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "tse1-tsu2-iau3-si7-tsiu2-tsing1-tso7-sing5-e5");
  print_state(api, session, "liantua_c1");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "tshin1-tshiunn7-li2-ka1-ti1-e5-mia5-tian7-ue7-ho7-be2");
  print_state(api, session, "liantua_c2");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "su7-au7-the3-tsiu2-liau2-au7");
  print_state(api, session, "liantua_c3");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "be7-ki3-tsit8-ka1-ti1-lim1-tsiu2");
  print_state(api, session, "liantua_c4");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "uan5-tsuan5-bo5-in3-siong7");
  print_state(api, session, "liantua_c5");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "lang5-lang2-jim7-ui5");
  print_state(api, session, "liantua_c6");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "si7-an2-tsuann2-e7-an2-ne1");
  print_state(api, session, "liantua_c7");
  api->clear_composition(session);

  // Mid-way selection: pick a word mid-composition, keep typing, commit.
  // Selects candidate index 1 (是按怎) for the first segment, then the rest
  // must compose without discarding the confirmed segment.
  api->simulate_key_sequence(session, "si7-an2-tsuann2-lang5");
  api->process_key(session, 0xFF09, 0);  // Tab: enter selection mode
  select_candidate_by_text(api, session, "\xe6\x98\xaf\xe6\x8c\x89\xe6\x80\x8e");  // 是按怎
  api->simulate_key_sequence(session, "the3-tsiu2");
  print_state(api, session, "liantua_midsel");
  api->simulate_key_sequence(session, " ");
  RIME_STRUCT(RimeCommit, liantua_commit);
  if (api->get_commit(session, &liantua_commit)) {
    std::cout << "COMMIT\tliantua_midsel\t" << sanitize(liantua_commit.text) << '\n';
    api->free_commit(&liantua_commit);
  } else {
    std::cout << "COMMIT\tliantua_midsel\t\n";
  }
  api->clear_composition(session);

  // 全羅 mode: whole-sentence commit with dictionary word boundaries.
  api->set_option(session, "full_romanization", true);
  api->simulate_key_sequence(session,
      "si7-an2-tsuann2-lang5-the3-tsiu2-liau2-au7");
  api->simulate_key_sequence(session, " ");  // confirm sentence candidate
  RIME_STRUCT(RimeCommit, full_roman_commit);
  if (api->get_commit(session, &full_roman_commit)) {
    std::cout << "COMMIT\tliantua_full_roman\t" << sanitize(full_roman_commit.text) << '\n';
    api->free_commit(&full_roman_commit);
  } else {
    std::cout << "COMMIT\tliantua_full_roman\t\n";
  }
  api->set_option(session, "full_romanization", false);
  api->clear_composition(session);

  // 全羅 mode: Tab selection must retain a chosen word in the composition.
  // Shift+s exercises the uppercase interception so capitalization does not
  // depend on scenario order within this shared session.
  api->set_option(session, "full_romanization", true);
  api->process_key(session, 0x73, 0x1);  // Shift+s → capitalize_next
  api->simulate_key_sequence(session, "i7-an2-tsuann2-lang5");
  api->process_key(session, 0xFF09, 0);  // Tab: enter selection mode
  if (!select_candidate_by_text(api, session, "\xe6\x98\xaf\xe6\x8c\x89\xe6\x80\x8e")) {
    std::cerr << "cannot select 是按怎 in full-roman mode\n";
    return 1;
  }
  print_state(api, session, "liantua_full_roman_midsel");
  RIME_STRUCT(RimeCommit, full_roman_mid_commit);
  if (api->get_commit(session, &full_roman_mid_commit)) {
    std::cout << "COMMIT\tliantua_full_roman_mid\t"
              << sanitize(full_roman_mid_commit.text) << '\n';
    api->free_commit(&full_roman_mid_commit);
  } else {
    std::cout << "COMMIT\tliantua_full_roman_mid\t\n";
  }
  api->simulate_key_sequence(session, "the3-tsiu2-liau2-au7");
  print_state(api, session, "liantua_full_roman_resumed");
  api->simulate_key_sequence(session, " ");
  RIME_STRUCT(RimeCommit, full_roman_resumed_commit);
  if (api->get_commit(session, &full_roman_resumed_commit)) {
    std::cout << "COMMIT\tliantua_full_roman_resumed\t"
              << sanitize(full_roman_resumed_commit.text) << '\n';
    api->free_commit(&full_roman_resumed_commit);
  } else {
    std::cout << "COMMIT\tliantua_full_roman_resumed\t\n";
  }
  api->clear_composition(session);
  api->set_option(session, "full_romanization", false);

  // 手動漢羅 (B): Tab selection + backslash marks the highlighted span as
  // romanization; unselected words stay hanzi. Roman segments follow poj_mode.
  api->set_option(session, "hanlo_manual", true);
  api->simulate_key_sequence(session, "si7-an2-tsuann2-lang5");
  api->process_key(session, 0xFF09, 0);  // Tab: enter selection mode
  if (!highlight_candidate_by_text(api, session, "\xe6\x98\xaf\xe6\x8c\x89\xe6\x80\x8e")) {
    std::cerr << "cannot highlight 是按怎 for manual mix\n";
    return 1;
  }
  api->process_key(session, 0x5C, 0);  // backslash: mark span as romanization
  print_state(api, session, "mixmark_mid");
  RIME_STRUCT(RimeCommit, mixmark_mid_commit);
  if (api->get_commit(session, &mixmark_mid_commit)) {
    std::cout << "COMMIT\tmixmark_mid\t" << sanitize(mixmark_mid_commit.text) << '\n';
    api->free_commit(&mixmark_mid_commit);
  } else {
    std::cout << "COMMIT\tmixmark_mid\t\n";
  }
  api->simulate_key_sequence(session, "");
  print_state(api, session, "mixmark_resumed");
  api->simulate_key_sequence(session, " ");
  RIME_STRUCT(RimeCommit, mixmark_final_commit);
  if (api->get_commit(session, &mixmark_final_commit)) {
    std::cout << "COMMIT\tmixmark_final\t" << sanitize(mixmark_final_commit.text) << '\n';
    api->free_commit(&mixmark_final_commit);
  } else {
    std::cout << "COMMIT\tmixmark_final\t\n";
  }
  api->clear_composition(session);

  // Same journey in POJ: the marked segment must come out as POJ romanization.
  api->set_option(session, "poj_mode", true);
  api->simulate_key_sequence(session, "si7-an2-tsuann2-lang5");
  api->process_key(session, 0xFF09, 0);
  if (!highlight_candidate_by_text(api, session, "\xe6\x98\xaf\xe6\x8c\x89\xe6\x80\x8e")) {
    std::cerr << "cannot highlight 是按怎 for manual mix POJ\n";
    return 1;
  }
  api->process_key(session, 0x5C, 0);
  api->simulate_key_sequence(session, "");
  api->simulate_key_sequence(session, " ");
  RIME_STRUCT(RimeCommit, mixmark_poj_commit);
  if (api->get_commit(session, &mixmark_poj_commit)) {
    std::cout << "COMMIT\tmixmark_poj\t" << sanitize(mixmark_poj_commit.text) << '\n';
    api->free_commit(&mixmark_poj_commit);
  } else {
    std::cout << "COMMIT\tmixmark_poj\t\n";
  }
  api->set_option(session, "poj_mode", false);

  // 手動漢羅: two segments marked/picked in order — mark 是按怎 as roman,
  // Tab-pick 人 as hanzi — then Space assembles mix + hanzi remainder 退.
  api->simulate_key_sequence(session, "si7-an2-tsuann2-lang5-the3");
  api->process_key(session, 0xFF09, 0);
  if (!highlight_candidate_by_text(api, session, "\xe6\x98\xaf\xe6\x8c\x89\xe6\x80\x8e")) {
    std::cerr << "cannot highlight 是按怎 for two-mark mix\n";
    return 1;
  }
  api->process_key(session, 0x5C, 0);  // mark 是按怎 as roman
  api->process_key(session, 0xFF09, 0);  // Tab again for the next word
  if (!select_candidate_by_text(api, session, "\xe4\xba\xba")) {  // 人 as hanzi
    std::cerr << "cannot select 人 for two-mark mix\n";
    return 1;
  }
  print_state(api, session, "mixmark_two_mid");
  api->simulate_key_sequence(session, " ");
  RIME_STRUCT(RimeCommit, mixmark_two_commit);
  if (api->get_commit(session, &mixmark_two_commit)) {
    std::cout << "COMMIT\tmixmark_two\t" << sanitize(mixmark_two_commit.text) << '\n';
    api->free_commit(&mixmark_two_commit);
  } else {
    std::cout << "COMMIT\tmixmark_two\t\n";
  }
  api->clear_composition(session);

  // 手動漢羅 lifecycle: marking, then Escape cancels the composition; a
  // fresh marking journey must not inherit the cancelled mix state (a leak
  // would double the roman prefix).
  api->simulate_key_sequence(session, "si7-an2-tsuann2-lang5");
  api->process_key(session, 0xFF09, 0);
  if (!highlight_candidate_by_text(api, session, "\xe6\x98\xaf\xe6\x8c\x89\xe6\x80\x8e")) {
    std::cerr << "cannot highlight 是按怎 for escape lifecycle\n";
    return 1;
  }
  api->process_key(session, 0x5C, 0);  // mark 是按怎 as roman
  api->process_key(session, 0xFF1B, 0);  // Escape cancels the composition
  api->clear_composition(session);
  api->simulate_key_sequence(session, "si7-an2-tsuann2-lang5");
  api->process_key(session, 0xFF09, 0);
  if (!highlight_candidate_by_text(api, session, "\xe6\x98\xaf\xe6\x8c\x89\xe6\x80\x8e")) {
    std::cerr << "cannot highlight 是按怎 after escape\n";
    return 1;
  }
  api->process_key(session, 0x5C, 0);
  api->simulate_key_sequence(session, " ");
  RIME_STRUCT(RimeCommit, mixmark_afteresc_commit);
  if (api->get_commit(session, &mixmark_afteresc_commit)) {
    std::cout << "COMMIT\tmixmark_afteresc\t" << sanitize(mixmark_afteresc_commit.text) << '\n';
    api->free_commit(&mixmark_afteresc_commit);
  } else {
    std::cout << "COMMIT\tmixmark_afteresc\t\n";
  }
  api->clear_composition(session);
  api->set_option(session, "hanlo_manual", false);
  api->clear_composition(session);

  // Tone-1 digitless input (車 tshia1): both TL and POJ spellings must
  // surface the character without requiring the tone digit, and the POJ
  // form must not fragment into syllable pieces.
  api->simulate_key_sequence(session, "tshia");
  print_state(api, session, "tone1_tshia");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "chhia");
  print_state(api, session, "tone1_chhia");
  api->clear_composition(session);

  api->simulate_key_sequence(session, "chhia1");
  print_state(api, session, "tone1_chhia1");
  api->clear_composition(session);

  // Checked tones (4/8 with -t/-p/-k/-h codas) and further POJ families:
  // digitless input must behave the same in TL and POJ spellings.
  // 節 tsat4/chat4, 石 tsioh8/chioh8, 豬 tsu1/chu1, 英 ing1/eng1,
  // 山 suann1/soann1 (ua->oa). Tone-4 tone digit sanity at the end.
  api->simulate_key_sequence(session, "tsat");
  print_state(api, session, "tone4_tsat");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "chat");
  print_state(api, session, "tone4_chat");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "tsioh");
  print_state(api, session, "tone8_tsioh");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "chioh");
  print_state(api, session, "tone8_chioh");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "tsu");
  print_state(api, session, "tone1_tsu");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "chu");
  print_state(api, session, "tone1_chu");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "ing");
  print_state(api, session, "tone1_ing");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "eng");
  print_state(api, session, "tone1_eng");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "suann");
  print_state(api, session, "tone1_suann");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "soann");
  print_state(api, session, "tone1_soann");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "chat4");
  print_state(api, session, "tone4_chat4");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "chioh8");
  print_state(api, session, "tone8_chioh8");
  api->clear_composition(session);

  // Remaining checked codas at tone 4 (-p: 接 tsiap4/chiap, -k: 積
  // tsik4/chik) and the landing-page promise 食 tsiah8/chiah (tone 8, -h).
  api->simulate_key_sequence(session, "tsiap");
  print_state(api, session, "tone4_tsiap");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "chiap");
  print_state(api, session, "tone4_chiap");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "tsik");
  print_state(api, session, "tone4_tsik");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "chik");
  print_state(api, session, "tone4_chik");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "tsiah");
  print_state(api, session, "landing_tsiah");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "chiah");
  print_state(api, session, "landing_chiah");
  api->clear_composition(session);

  // Diagnostic control: toned form of the failing digitless probe.
  api->simulate_key_sequence(session, "tsiah8");
  print_state(api, session, "landing_tsiah8");
  api->clear_composition(session);

  // Digitless hyphenated dict word (頭前 thau5 tsing5): the word must be a
  // candidate directly, matching toned input behavior.
  api->simulate_key_sequence(session, "tai-uan");
  print_state(api, session, "taiuan_digitless");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "uan");
  print_state(api, session, "single_uan");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "tsing");
  print_state(api, session, "single_tsing");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "tsi");
  print_state(api, session, "single_tsi");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "tsit");
  print_state(api, session, "single_tsit");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "thau");
  print_state(api, session, "single_thau");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "ah");
  print_state(api, session, "single_ah");
  api->clear_composition(session);
  // Coda-h omission fuzzy (derive/h$//): typing POJ without the final -h
  // (chia/chio) must still surface 食/石.
  api->simulate_key_sequence(session, "chia");
  print_state(api, session, "fuzzy_chia");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "chio");
  print_state(api, session, "fuzzy_chio");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "tsia");
  print_state(api, session, "single_tsia");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "phah");
  print_state(api, session, "single_phah");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "pah");
  print_state(api, session, "single_pah");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "siah");
  print_state(api, session, "single_siah");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "thau-tsing");
  print_state(api, session, "tl_multi_digitless");
  api->clear_composition(session);

  // Multi-syllable POJ word with ts->ch in the SECOND syllable
  // (頭前 thau5 tsing5 -> thau5 cheng5): algebra applies per syllable.
  api->simulate_key_sequence(session, "thau5-cheng5");
  print_state(api, session, "poj_multi_toned");
  api->clear_composition(session);

  // MOE dictionary entries (學科術語/地名) reachable via toneless POJ
  // spellings: oan-lim (員林), kong-hap-chok-iong (光合作用).
  api->simulate_key_sequence(session, "oan-lim");
  print_state(api, session, "poj_yuanlin");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "kong-hap-chok-iong");
  print_state(api, session, "poj_konghap");
  api->clear_composition(session);
  api->simulate_key_sequence(session, "uan-lim");
  print_state(api, session, "tl_yuanlin");
  api->clear_composition(session);
  api->destroy_session(session);
  api->finalize();
  dlclose(lua);
  return 0;
}
