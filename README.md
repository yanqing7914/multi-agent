# multi-agent

闈㈠悜 Codex銆丆ursor銆丆laude Code銆丱penClaw銆丠ermes銆乂S Code 鐨勫 Agent 鍗忎綔鍗忚銆丼kill 涓?MCP 璁捐銆?
鏈粨搴撳綋鍓嶅寘鍚涓€鐗?`multi-agent-coding` Skill锛屼互鍙婂悗缁?MCP/IDE 鎻掍欢鐨勬帴鍙ｈ鏍兼枃妗ｃ€傚畠鐨勭洰鏍囦笉鏄仛涓€涓け鎺х殑 agent swarm锛岃€屾槸璁╁涓?agent 鍦ㄥ鏉傚伐绋嬩换鍔′腑鎸夆€滀换鍔″崱銆佹潈闄愯竟鐣屻€佽瘎瀹°€侀獙璇併€佹渶缁堥泦鎴愨€濈殑鏂瑰紡鍗忎綔銆?
## 椤圭洰瀹氫綅

```text
Skill = 鍗忎綔鏂规硶璁哄拰鎻愮ず璇嶈绾?MCP = 浠诲姟銆佺姸鎬併€佸鎵广€佽瘎瀹″拰瀹¤鐨勫伐鍏峰悗绔?IDE Plugin = 鍥惧舰鍖栦换鍔￠潰鏉裤€丳rompt 鐢熸垚鍣ㄥ拰鏈湴闆嗘垚鍏ュ彛
```

褰撳墠宸插疄鐜扮殑鏄?Skill 鍜屾枃妗ｈ鏍硷紱MCP Server 涓?IDE 鎻掍欢灞炰簬鍚庣画瀹炵幇鏂瑰悜銆?
## multi-agent-coding Skill

`multi-agent-coding` 鏄竴涓?prompt-guided 鐨勫 Agent 缂栫爜鍗忎綔 Skill锛岀敤浜庢寚瀵?agent 鍦ㄥ鏉備唬鐮佷换鍔′腑瀹屾垚锛?
```text
闇€姹傜悊瑙?鈫?鐜妫€鏌?鈫?浠诲姟鎷嗚В 鈫?骞惰璋冪爺 鈫?鍙楁帶瀹炵幇 鈫?Diff 瀹¤ 鈫?澶氳瑙掕瘎瀹?鈫?楠岃瘉 鈫?鏈€缁堜氦浠?```

鏍稿績瑙掕壊锛?
- `Main Agent`锛氫富鎺э紝璐熻矗瑙勫垝銆佸垎娲俱€侀泦鎴愩€侀獙璇佸拰鏈€缁堜氦浠樸€?- `Explorer`锛氬彧璇昏皟鐮斾唬鐮併€佹灦鏋勩€佹祴璇曘€佺害瀹氬拰椋庨櫓銆?- `Worker`锛氬湪 `allowed_paths` 鍐呭彈鎺у疄鐜帮紝涓嶅緱瓒婃潈銆?- `Reviewer`锛氬彧璇昏瘎瀹★紝涓嶆敼浠ｇ爜锛屽彲浣跨敤 `ssrd` 绛夎瘎瀹?Skill銆?- `Verifier`锛氳繍琛屾垨鎻忚堪娴嬭瘯銆佹瀯寤恒€乴int銆佸鐜版楠ゃ€?- `Integrator`锛氶€氬父鐢?Main Agent 鎵紨锛岃礋璐ｅ悎骞跺拰鏈€缁堜竴鑷存€с€?
## 鑳借В鍐充粈涔堥棶棰?
- 澶嶆潅浠诲姟鎷嗕笉娓咃紝瀹规槗杈瑰仛杈圭寽銆?- 澶у瀷浠ｇ爜搴撲笂涓嬫枃澶ぇ锛岄渶瑕佸涓?Explorer 骞惰璋冪爺銆?- 鍓嶅悗绔€佸悗绔€佹祴璇曘€佹枃妗ｇ瓑浠诲姟鍙互鍒嗗伐锛屼絾瀹规槗浜掔浉瑕嗙洊銆?- Worker 浣跨敤鍏朵粬 Skill 鏃剁己灏戞巿鏉冭竟鐣屻€?- 澶氫釜 reviewer 鐨勬剰瑙侀渶瑕佸幓閲嶃€佹帓搴忓拰姹囨€汇€?- 鏈€缁堜氦浠樺墠缂哄皯 Diff 瀹¤鍜岄獙璇侀棴鐜€?
## 閲嶈璇存槑

杩欎釜 Skill 鏄崗浣滆绾︼紝涓嶆槸瀹夊叏娌欑锛屼篃涓嶆槸鑷姩缂栨帓鍣ㄣ€傚畠涓嶈兘鐪熸寮哄埗闅旂鏂囦欢绯荤粺銆佺綉缁溿€丟it 鎴栬繘绋嬫潈闄愩€?
瀹冩彁渚涚殑鏄細

- 浠€涔堟椂鍊欏簲璇ヤ娇鐢ㄥ Agent銆?- 濡備綍鍐欎换鍔″崱銆?- Worker 鑳芥敼鍝簺璺緞銆?- Worker 浠€涔堟椂鍊欏彲浠ヤ娇鐢ㄥ叾浠?Skill銆?- Reviewer 濡備綍鍙璇勫銆?- Main Agent 濡備綍瀹¤ Diff 鍜屾眹鎬荤粨鏋溿€?
鐪熸鐨勭姸鎬佺鐞嗐€佹潈闄愭鏌ャ€佷换鍔￠潰鏉垮拰瀹¤宸ュ叿锛屽缓璁€氳繃鍚庣画 MCP Server 鍜?IDE 鎻掍欢瀹炵幇銆?
## 鐩綍缁撴瀯

```text
SKILL.md                         # Codex/OpenClaw 椋庢牸 Skill 涓绘枃浠?agents/openai.yaml               # Codex UI 鍏冩暟鎹?templates/task-card.md           # 瀛愪换鍔″崱妯℃澘
templates/result-report.md       # 瀛?Agent 缁撴灉鎶ュ憡妯℃澘
templates/final-delivery.md      # 鏈€缁堜氦浠樻ā鏉?checklists/                      # 鍚敤澶?Agent銆佺幆澧冦€佹潈闄愩€佸畨鍏ㄣ€丏iff 瀹¤妫€鏌ユ竻鍗?examples/                        # feature / bugfix / review 绀轰緥娴佺▼
docs/clients.md                  # Codex/Cursor/Claude/OpenClaw/Hermes/VS Code 鏀寔妯″瀷
docs/mcp-format.md               # MCP 宸ュ叿銆佽祫婧愩€丳rompt 鏍煎紡瑙勬牸
```

## 瑙﹀彂鏉′欢

閫傚悎瑙﹀彂 `multi-agent-coding` 鐨勬儏鍐碉細

- 鐢ㄦ埛鏄庣‘璇粹€滅敤澶氫釜 agent鈥濃€滃紑 subagent鈥濃€滃苟琛屽鐞嗏€濃€滃涓?reviewer 璇勫鈥濄€?- 浠诲姟娑夊強澶氫釜鐙珛妯″潡鎴栨妧鏈眰锛屼緥濡傚墠绔€佸悗绔€佹暟鎹簱銆佹祴璇曘€?- 闇€瑕佸厛璋冪爺鍐嶅疄鐜帮紝鍐嶈瘎瀹″拰楠岃瘉銆?- 浠ｇ爜搴撹緝澶э紝鍗?agent 涓婁笅鏂囧帇鍔涢珮銆?- 鐢ㄦ埛瑕佹眰澶氳瑙掕瘎瀹°€佸畨鍏ㄥ鏌ャ€佹灦鏋勫鏌ャ€佸鏉?bug 瀹氫綅銆?- Worker 闇€瑕佷娇鐢ㄥ叾浠?Skill锛屼絾蹇呴』鏈夋潈闄愯竟鐣屻€?
涓嶅缓璁Е鍙戠殑鎯呭喌锛?
- 鍗曟枃浠跺皬鏀瑰姩銆?- 鏄庣‘鐨勫皬 bug銆?- 绠€鍗曡В閲婁唬鐮併€?- 鏀规枃妗堛€佹敼閰嶇疆瀛楁绛夎交閲忎换鍔°€?- 娌℃湁瀹夊叏鐨勪换鍔℃媶鍒嗚竟鐣屻€?
## Quick Path 涓?Multi-Agent Path

灏忎换鍔¤蛋 Quick Path锛?
```text
Intake 鈫?Plan Lite 鈫?Implement/Answer 鈫?Review Lite 鈫?Verify 鈫?Deliver
```

澶嶆潅浠诲姟璧?Multi-Agent Path锛?
```text
Intake 鈫?Environment Check 鈫?Task Graph 鈫?Explorer Fan-out 鈫?Synthesis 鈫?Scoped Worker 鈫?Diff Audit 鈫?Reviewer 鈫?Verifier 鈫?Deliver
```

## Worker 浣跨敤鍏朵粬 Skill 鐨勮鍒?
Worker 鍙互浣跨敤鍏朵粬 Skill锛屼絾涓嶈兘鍊?Skill 瓒婃潈銆?
Worker 浣跨敤 Skill 蹇呴』婊¤冻锛?
- Skill 鍦ㄤ换鍔″崱鐨?`may_use_skills` 涓紝鎴?Main Agent 鏄庣‘鎵瑰噯銆?- Skill 涓庡綋鍓?Worker 鐩爣鐩存帴鐩稿叧銆?- 涓嶆墿澶?`allowed_paths`銆?- 涓嶈繍琛?`blocked_commands`銆?- 涓嶈闂?secret銆乼oken銆乧ookie銆丼SH key銆佷簯鍑嵁绛夋晱鎰熸枃浠躲€?- 涓嶆敼鍙?Worker 鐨勮鑹诧紝渚嬪浠庡疄鐜拌€呭彉鎴愰儴缃茶€呮垨 Git 鎿嶄綔鑰呫€?
濡傛灉涓嶆弧瓒虫潯浠讹紝Worker 蹇呴』鍋滄骞舵彁浜?`Skill Use Request`銆?
绀轰緥锛氬涓?agent 浣跨敤 `ssrd` 璇勫鏂规鏃讹紝搴斿垱寤哄涓彧璇?`Reviewer`锛岃€屼笉鏄啓鏉冮檺 Worker锛?
```yaml
mode: review
role: Reviewer
may_use_skills:
  - ssrd
write_permission: false
may_spawn_subagents: false
```

## 璺ㄥ鎴风鏀寔

鏈粨搴撶洰鏍囨敮鎸侊細

- Codex
- Cursor
- Claude Code
- OpenClaw
- Hermes
- VS Code

涓嶅悓瀹㈡埛绔殑 agent 鍚姩鏂瑰紡銆佹彃浠舵満鍒躲€丮CP 閰嶇疆涓嶅悓锛屼絾鍏变韩鐨勫崗璁簲璇ヤ繚鎸佷竴鑷达細

- Task Card
- Result Report
- Role Permission
- Skill Use Approval
- Review Finding
- Scope Audit
- Final Delivery

璇︾粏璁捐瑙侊細

- `docs/clients.md`
- `docs/mcp-format.md`

## MCP 璁捐鏂瑰悜

鍚庣画鍙互瀹炵幇涓€涓?`multi-agent-coordinator-mcp`锛岀敤浜庢彁渚涳細

- `create_task`
- `list_tasks`
- `get_task`
- `update_task_status`
- `record_result`
- `check_path_allowed`
- `record_touched_paths`
- `request_skill_use`
- `approve_skill_use`
- `record_finding`
- `summarize_review`
- `audit_scope`
- `generate_final_report`

MCP 璐熻矗鐘舵€佸拰宸ュ叿鍖栨搷浣滐紝Skill 璐熻矗鍗忎綔娴佺▼鍜岃涓鸿竟鐣屻€?
## IDE 鎻掍欢鏂瑰悜

鍚庣画鍙互鏀寔 VS Code / Cursor 鎻掍欢锛屾彁渚涳細

- Task Board锛氭煡鐪?pending/running/blocked/completed 浠诲姟銆?- Create Task锛氬浘褰㈠寲鍒涘缓 Explorer/Worker/Reviewer/Verifier 浠诲姟鍗°€?- Findings View锛氬睍绀?reviewer findings锛屽苟鏀寔璺宠浆鏂囦欢琛屽彿銆?- Skill Approval Center锛氱鐞?Worker/Reviewer 浣跨敤鍏朵粬 Skill 鐨勫鎵广€?- Scope Audit锛氫竴閿鏌?Worker 鏄惁瓒婄晫銆佹槸鍚︽湁鍐茬獊銆?- Prompt Generator锛氫负 Codex銆丆ursor銆丆laude Code銆丱penClaw銆丠ermes 鐢熸垚閫傞厤 prompt銆?- Final Report锛氫竴閿敓鎴愭渶缁堜氦浠樻憳瑕併€?
## 浣跨敤鏂瑰紡

灏嗘湰鐩綍澶嶅埗鍒?Codex Skill 鐩綍锛屾垨浣滀负椤圭洰鍐?Skill 浣跨敤锛岀劧鍚庢樉寮忚皟鐢細

```text
Use $multi-agent-coding to coordinate this coding task with scoped roles, review, and verification.
```

涓枃绀轰緥锛?
```text
浣跨敤 $multi-agent-coding锛屾妸杩欎釜鍔熻兘鎷嗘垚 Explorer銆乄orker銆丷eviewer 鍜?Verifier 鏉ュ仛銆?```

```text
浣跨敤 $multi-agent-coding锛屽紑澶氫釜 Reviewer锛屽苟璁╁畠浠敤 ssrd 璇勫杩欎釜鏂规銆?```

```text
浣跨敤 $multi-agent-coding锛屽垽鏂繖涓换鍔℃槸鍚﹀€煎緱寮€澶氫釜 agent锛涘鏋滀笉鍊煎緱锛屽氨璧?Quick Path銆?```

## 褰撳墠鐘舵€?
- 宸插畬鎴愶細`multi-agent-coding` Skill v0.1銆?- 宸插畬鎴愶細浠诲姟鍗°€佺粨鏋滄姤鍛娿€佹渶缁堜氦浠樻ā鏉裤€?- 宸插畬鎴愶細鐜銆佹潈闄愩€佸畨鍏ㄣ€丏iff 瀹¤妫€鏌ユ竻鍗曘€?- 宸插畬鎴愶細Codex/Cursor/Claude Code/OpenClaw/Hermes/VS Code 鏀寔妯″瀷鏂囨。銆?- 宸插畬鎴愶細MCP 鏍煎紡鏂囨。銆?- 寰呭疄鐜帮細MCP Server銆?- 寰呭疄鐜帮細VS Code / Cursor IDE 鎻掍欢銆?
## 璺嚎鍥?
```text
v0.1 Skill锛氬崗浣滄祦绋嬨€佷换鍔″崱銆佹潈闄愯竟鐣屻€佽瘎瀹″拰楠岃瘉妯℃澘
v0.2 MCP Server锛氫换鍔＄姸鎬併€佸鎵广€乫inding銆乻cope audit銆乫inal report
v0.3 VS Code / Cursor Plugin锛氫换鍔￠潰鏉裤€丳rompt 鐢熸垚鍣ㄣ€佸璁¤鍥?v0.4 Client Adapters锛欳laude Code銆丱penClaw銆丠ermes 閫傞厤
v0.5 Worktree / PR / CI锛氬苟琛屽垎鏀€丳R review銆丆I 澶辫触鍥炴祦
```
