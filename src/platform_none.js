/* No host behind the page: the dev server, and any plain web build.

   Every method is the honest no-op rather than a stub that logs - the shell
   calls these on every level start and every pause, and a chatty console here
   would bury the lines that matter. Storage is the browser's own. */
const PLATFORM = {
  name: "none",
  init() { return Promise.resolve(); },
  storage: localStore,
  loadingStart() {}, loadingStop() {},
  gameplayStart() {}, gameplayStop() {},
  happytime() {},
  hostMuted() { return false; },
  onHostMuteChange() {},
};
