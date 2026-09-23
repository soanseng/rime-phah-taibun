#include <dlfcn.h>

#include <iostream>
#include <string>

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
            << context.menu.num_candidates << '\n';
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

}  // namespace

int main(int argc, char* argv[]) {
  if (argc != 4) {
    std::cerr << "usage: rime_smoke LUA_PLUGIN SHARED_DATA USER_DATA\n";
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

  api->simulate_key_sequence(session, "`");
  print_state(api, session, "backtick");
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

  api->destroy_session(session);
  api->finalize();
  dlclose(lua);
  return 0;
}
