#!/bin/bash
# spaces.sh — the agent's hands on windows and Spaces (Silo One). A Mac has many desktops (Spaces), and a full-screen
# window is a Space of its own; a window that is "behind" is usually on another Space. Never tell the owner to swipe: bring
# the window over, or show the page on the console's Browser page (console.sh browser open) and say so.
#   spaces.sh front                      which app is in front, its window's title, whether it is full screen
#   spaces.sh to <app> [window words]    bring an app forward across Spaces (the Mac follows to its Space); with words, the
#                                        window whose title has them comes to the top; the result names what is in front now
#   spaces.sh windows <app>              the app's windows, by title (the process must have windows on some Space)
#   spaces.sh next | prev                one Space to the right or the left (Control-arrow: the keyboard's swipe)
#   spaces.sh back                       back to the app that was in front before the last `to` (remembered for the turn)
# Needs Accessibility for the terminal the agent runs under (System Settings > Privacy & Security > Accessibility). Apps are
# named as the Mac names them: "Google Chrome", "Comet", "Terminal", "Finder".
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; MEM="$ROOT/data/cache/spaces-back"
osa() { osascript -e "$1" 2>&1; }
front() {
  # the process first, then its window by that name: a window asked of a "whose" reference fails with an invalid index
  local p t fs
  p="$(osa 'tell application "System Events" to get name of first application process whose frontmost is true')"
  t="$(osa "tell application \"System Events\" to tell process \"$p\" to get name of window 1" 2>/dev/null)"; case "$t" in *"execution error"*) t="";; esac
  fs="$(osa "tell application \"System Events\" to tell process \"$p\" to get value of attribute \"AXFullScreen\" of window 1" 2>/dev/null)"
  local who="$p"; [ "$p" = "app_mode_loader" ] && who="a Chrome app window${t:+ (\"$t\")}"
  printf 'in front: %s' "$who"; [ -n "$t" ] && [ "$p" != "app_mode_loader" ] && printf ' · window "%s"' "$t"; [ "$fs" = "true" ] && printf ' · full screen (a Space of its own)'; echo
}
case "${1:-front}" in
  front) front;;
  windows)
    [ -n "$2" ] || { echo 'spaces.sh windows "<app>"'; exit 1; }
    osa "tell application \"System Events\" to tell process \"$2\" to get name of every window" | sed 's/, /\n/g' | sed '/^$/d;s/^/  /';;
  to)
    [ -n "$2" ] || { echo 'spaces.sh to "<app>" [window words]'; exit 1; }
    app="$2"; words="${3:-}"
    mkdir -p "$(dirname "$MEM")"; osa 'tell application "System Events" to get name of first application process whose frontmost is true' >"$MEM" 2>/dev/null
    # by the app's name first (Google Chrome, Comet, Finder); by its process name when the app is known to the Mac otherwise (WezTerm is wezterm-gui)
    osa "tell application \"$app\" to activate" >/dev/null 2>&1 || osa "tell application \"System Events\" to set frontmost of process \"$app\" to true" >/dev/null
    if [ -n "$words" ]; then
      osa "tell application \"System Events\" to tell process \"$app\"
        set frontmost to true
        try
          perform action \"AXRaise\" of (first window whose name contains \"$words\")
        end try
      end tell" >/dev/null
    else
      osa "tell application \"System Events\" to tell process \"$app\"
        set frontmost to true
        try
          perform action \"AXRaise\" of window 1
        end try
      end tell" >/dev/null
    fi
    sleep 0.6; front;;
  back)
    prev="$(cat "$MEM" 2>/dev/null)"; [ -n "$prev" ] || { echo "nothing to go back to"; exit 1; }
    osa "tell application \"System Events\" to set frontmost of process \"$prev\" to true" >/dev/null; sleep 0.5; front;;
  next|prev)
    code=124; [ "$1" = prev ] && code=123
    osa "tell application \"System Events\" to key code $code using control down" >/dev/null; sleep 0.7; front;;
  *) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0";;
esac
