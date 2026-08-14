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

  api->simulate_key_sequence(session, "tsiah8 ");
  api->simulate_key_sequence(session, "qxyz");
  print_state(api, session, "origin_after_commit");

  api->destroy_session(session);
  api->finalize();
  dlclose(lua);
  return 0;
}
