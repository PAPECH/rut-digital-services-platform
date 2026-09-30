// OpenAppButton payload the bot sends for its policy button (bot/app/main.py's
// _POLICY_START_PARAM) -- lands in initDataUnsafe.start_param, read via getStartParam() in
// @/max/bridge. Not a plausible real campaign-link id, so App.tsx's generic start_param
// handling can tell "show the policy screen" apart from "report a campaign link open".
export const POLICY_START_PARAM = "__policy__";
