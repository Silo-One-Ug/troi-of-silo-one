// The brain's tools, named in a few words with a small icon: what a step on the working line says, and what an agent's
// step says on the Agents page. One place for both (moved out of chat.tsx, 2026-09-27).
import { AlarmClock, AppWindow, AudioLines, Bot, Braces, Brain, CalendarDays, Camera, ChartLine, Coins, Command as CommandKey, Container, ExternalLink, FileCode2, FilePen, FilePlus, FileText, FolderInput, FolderSearch, GitBranch, GitPullRequest, Github, Globe, Hand, HardDrive, HeartPulse, Image as ImageIcon, LayoutGrid, Layers, Link2, ListChecks, Mail, Mic, MonitorCog, Music, Newspaper, Plug, Presentation, ScanEye, Send, Server, Sparkles, Terminal, TextSearch, Users, Wrench } from "lucide-react";

// ---- the tools, each with a few words and a small icon
export const NOTE: Record<string, string> = { Bash: "at the terminal", Read: "reading a file", Write: "writing a file", Edit: "editing a file", MultiEdit: "editing a file", NotebookEdit: "editing a notebook", Glob: "looking through files", Grep: "searching files", WebSearch: "searching the web", WebFetch: "reading a page", Task: "delegating", Agent: "delegating", ToolSearch: "" };
export const TOOL_ICON: Record<string, any> = { Bash: Terminal, Read: FileText, Write: FilePlus, Edit: FilePen, MultiEdit: FilePen, NotebookEdit: FilePen, Glob: FolderSearch, Grep: TextSearch, WebSearch: Globe, WebFetch: Link2, Task: Bot, Agent: Bot };
export const GOOGLE: [RegExp, string, any][] = [[/calendar|event/, "in Google Calendar", CalendarDays], [/gmail|mail|message|draft|label|thread/, "in Gmail", Mail], [/task/, "in Google Tasks", ListChecks], [/contact|people/, "in Google Contacts", Users], [/drive|doc|sheet|form|slide|file|folder/, "in Google Drive", HardDrive]];
export function kind(tool: string): { label: string; Icon: any } {
  if (tool in NOTE) return { label: NOTE[tool], Icon: TOOL_ICON[tool] || Wrench };
  if (!tool.startsWith("mcp__")) return { label: "using " + tool, Icon: Wrench };
  const [, server = "", ...rest] = tool.split("__"); const fn = rest.join(" ").replace(/_/g, " ");
  if (server === "google") { const g = GOOGLE.find(([re]) => re.test(fn)); return g ? { label: g[1], Icon: g[2] } : { label: "in Google", Icon: Plug }; }
  if (/playwright|browser|chrome/.test(server)) return { label: "in the browser", Icon: AppWindow };
  if (/hands/.test(server)) return { label: "using the hands", Icon: Hand };
  return { label: "using " + server.replace(/[-_]/g, " "), Icon: Plug };
}
// a command on the working line is said by what it does (which of the agent's tools it runs, or which program), with its own
// icon, and the exact command sits beside the words in small type (a leading `cd "…" &&` left off the row; whole in the tooltip).
export const DOING: [RegExp, string, any][] = [
  [/\bboards\.sh\b/, "sorting the boards", Layers], [/\bboard\.sh\b|\bboard-state\.sh\b|\bshow-image\.sh\b/, "putting it on the board", Presentation], [/\bshow\.py\b/, "drawing a panel", LayoutGrid],
  [/\bpictures\.py\b/, "finding pictures", ImageIcon], [/\bimagine\.py\b/, "making a picture", Sparkles], [/\bnews\.py\b/, "reading the news", Newspaper], [/\bsounds\.py\b/, "at the sounds", AudioLines],
  [/\bcredits\.sh\b/, "checking the voice's credits", Coins], [/\bmedia\.py\b/, "at the music", Music], [/\bspaces\.sh\b|\bapps\.sh\b|\bcursor\.sh\b/, "moving windows about", AppWindow],
  [/\bconsole\.sh\b/, "steering the console", MonitorCog], [/\bbrain\.sh\b/, "picking a brain", Brain], [/\blook-screen\.sh\b|\bshare\.sh\b/, "taking a look at the screen", ScanEye], [/\blook\.sh\b/, "looking through the camera", Camera],
  [/\bfs\.sh\b/, "tidying files", FolderInput], [/\bremind\.sh\b/, "setting a reminder", AlarmClock], [/\btelegram\.py\b/, "reaching your phone", Send], [/\bmeeting\.py\b/, "on the meeting", Mic], [/\bservers\.py\b/, "checking the servers", HeartPulse],
  [/\bgrafana\.py\b/, "in Grafana", ChartLine], [/\bagenda\.py\b/, "reading your calendar", CalendarDays], [/\bpr\.py\b/, "on a pull request", GitPullRequest], [/\bci-status\.sh\b|\bgh\b/, "on GitHub", Github], [/\bgit\b/, "in the repository", GitBranch],
  [/\bcurl\b|\bwget\b/, "asking a server", Globe], [/\bssh\b|\bscp\b/, "on a server", Server], [/\bdocker\b|\bkubectl\b/, "among the containers", Container], [/\bnpx\b|\bnpm\b|\btsc\b|\bnode\b/, "in the console's code", Braces],
  [/\bpython3?\b/, "running a script", FileCode2], [/\b(?:grep|rg|find|ls|cat|head|tail|sed|awk|wc|stat|du|diff)\b/, "looking through files", FolderSearch], [/\bosascript\b/, "having a word with the Mac", CommandKey], [/\bopen\b/, "opening something", ExternalLink],
];
export function describe(tool: string, detail?: string): { Icon: any; label: string; note?: string; raw?: string } {
  const k = kind(tool);
  if (tool !== "Bash" || !detail) return { Icon: k.Icon, label: k.label, note: detail, raw: detail };
  const cmd = detail.replace(/^cd\s+(?:"[^"]*"|\S+)\s*&&\s*/, "");
  const hit = DOING.find(([re]) => re.test(cmd));
  return { Icon: hit ? hit[2] : Terminal, label: hit ? hit[1] : "at the terminal", note: cmd, raw: detail };
}
