# 报告生成请求（粘贴到部署好的 AI Learning Assistant，类型选 Essay）

先把 `<...>` 换成你的真实值、粘贴两份日志的内容，再提交。截图在生成后插入到 PDF/HTML 的 Figure 占位处。

---

Write the BA3073 take-home report "From AI Agent to Cloud Service" in English, at most 20 A4 pages.

Student: <姓名> (<学号>), BA3073, submitted <日期>.
Final HTTPS URL: https://<你的域名>/ui/ (protected by Nginx HTTP Basic Auth, separate from the BNBU login).
GitHub repository: <仓库链接>

Facts from my deployment (use only these; mark anything missing as [EVIDENCE NEEDED]):

Task 1 – local
- Machine: macOS, Apple Silicon (arm64), Docker Desktop <版本>.
- Commands: git clone; docker compose -p ai-learning-assistant up --build -d; curl http://127.0.0.1:14242/health returned {"status":"ok"}.
- Configured my own Qwen API key in model settings and generated a test artifact successfully.
- local-ui-check.txt:
<粘贴 local-ui-check.txt 全文>
- Figure 1: local UI at http://127.0.0.1:14242/ui/.

Prompt revision (backend/pipelines/essay_html.py)
- Original: a one-line system prompt ("expert teaching assistant ... self-contained HTML") plus a layout-only output contract.
- Revised: system prompt now requires grounding in the student's evidence and forbids invented results; a new [Report Guidance] block defines an 8-section structure, required technical explanations and an SVG request-path diagram, evidence rules (commands, expected vs observed, log excerpts, figure captions, [EVIDENCE NEEDED] placeholders), a security & cost section, prioritised improvements, secret redaction, and print rules (no page breaks inside figures/tables/code).
- Effect: <你观察到的变化，例如：结构更完整、包含日志与截图说明、不再编造结果>.

Task 2 – ECS
- ECS: <地域>, <规格>, <操作系统>, CPU <x86_64/aarch64>, public IP <IP>.
- Built linux/<amd64> image with docker buildx on the Mac and pushed to ACR <registry>/<namespace>/ai-learning-assistant:v1.
- On ECS: installed Docker, docker login to ACR, docker compose pull and up -d with ./data and ./workspace mounted as volumes; port mapping 0.0.0.0:14242->14242/tcp.
- Security group: TCP 14242 allowed only from my public IP /32.
- ecs-docker-check.txt:
<粘贴 ecs-docker-check.txt 全文>
- Figure 2: http://<IP>:14242/ui/ opened from my computer.

Task 3 – domain
- DNS A record <域名> -> <IP>; dig confirmed.
- Security group opened 80/443; Nginx reverse proxy to 127.0.0.1:14242; Certbot (Let's Encrypt) certificate, HTTP redirects to HTTPS.
- Nginx Basic Auth: request without credentials returned 401, with credentials 200.
- Afterwards changed port mapping to 127.0.0.1:14242:14242 and removed the public 14242 rule; HTTPS still works.
- Figure 3: browser Basic Auth prompt at https://<域名>/ui/. Figure 4: UI after authentication with padlock and address bar.

Problems and fixes: <真实遇到的问题，例如 arm64 镜像在 amd64 ECS 上 exec format error → 用 buildx --platform linux/amd64 重建；ICP 备案；ACR 登录失败等>.
Cost: <ECS 每月费用、带宽、域名、模型 token 费用>.
