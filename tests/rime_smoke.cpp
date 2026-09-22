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
  api->simulate_key_sequence(session, "d");  // index 2: 橋
  api->simulate_key_sequence(session, "tiann");
  print_state(api, session, "word_by_word_mid");
  api->process_key(session, 0xFF09, 0);
  api->simulate_key_sequence(session, "d");  // index 2: 鼎
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

  api->destroy_session(session);
  api->finalize();
  dlclose(lua);
  return 0;
}
