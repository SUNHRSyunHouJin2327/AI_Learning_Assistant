from __future__ import annotations

import json
from typing import Any, Callable

from backend.artifacts.filesystem import ArtifactRun
from backend.pipelines.authorship import add_author_credit
from backend.pipelines.common import (
    PipelineError,
    PipelineResult,
    extract_fenced_or_raw,
    format_citations,
    format_log,
)
from backend.pipelines.html_to_pdf import (
    A4_PAGE,
    ConvertError,
    HtmlToPdfConverter,
)
from backend.providers.base import (
    ModelProviderError,
    TextGenerationProvider,
    TextGenerationRequest,
)
from backend.timing import RunTimingRecorder, measure_stage


def run_essay_html_pipeline(
    *,
    artifact_run: ArtifactRun,
    model_profile: dict[str, Any],
    model_provider: TextGenerationProvider,
    pdf_converter: HtmlToPdfConverter,
    task_text: str,
    context_bundle: str,
    output_preference: str | None,
    options: dict[str, Any] | None,
    search: dict[str, Any],
    max_output_tokens: int,
    emit_event: Callable[[str, str], None] | None = None,
    timing: RunTimingRecorder | None = None,
) -> PipelineResult:
    log_lines = [
        "Pipeline: essay_html",
        f"Output preference: {output_preference or 'pdf'}",
        "Stage: generate_source",
    ]
    system_prompt, user_prompt = build_essay_html_prompt(
        task_text=task_text,
        context_bundle=context_bundle,
        options=options or {},
        search=search,
    )
    if emit_event:
        emit_event("generate_source", "Generating essay HTML source")

    try:
        with measure_stage(timing, "provider_generation"):
            raw_output = model_provider.generate_text(
                TextGenerationRequest(
                    profile=model_profile,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_output_tokens=max_output_tokens,
                    temperature=0.2,
                )
            )
    except ModelProviderError as exc:
        raise PipelineError(
            exc.code,
            exc.message,
            stage="generate_source",
            log_lines=log_lines,
        ) from exc
    except Exception as exc:
        raise PipelineError(
            "provider_unavailable",
            "The model provider request failed.",
            stage="generate_source",
            log_lines=log_lines,
        ) from exc

    source = extract_fenced_or_raw(raw_output, accepted_languages={"html", "htm"})
    source = add_author_credit(source.strip()) + "\n"
    html_path = artifact_run.write_output(
        "main.html",
        source,
        kind="source",
        media_type="text/html",
    )
    log_lines.extend(["Output: output/main.html", "Stage: convert_pdf"])
    if emit_event:
        emit_event("convert_pdf", "Converting essay HTML to PDF")

    pdf_path = artifact_run.run_dir / "output" / "main.pdf"
    try:
        with measure_stage(timing, "convert_pdf"):
            convert_result = pdf_converter.convert(
                html_path=html_path,
                pdf_path=pdf_path,
                page_config=A4_PAGE,
            )
    except ConvertError as exc:
        artifact_run.write_log("convert.log", exc.log_text)
        raise PipelineError(
            "convert_failed",
            exc.message,
            stage="convert_pdf",
            log_lines=log_lines,
        ) from exc
    except Exception as exc:
        artifact_run.write_log(
            "convert.log",
            "HTML-to-PDF converter raised an unexpected error.\n",
        )
        raise PipelineError(
            "convert_failed",
            "HTML-to-PDF conversion failed.",
            stage="convert_pdf",
            log_lines=log_lines,
        ) from exc

    artifact_run.write_log("convert.log", convert_result.log_text)
    artifact_run.write_output(
        "main.pdf",
        convert_result.pdf_path.read_bytes(),
        kind="pdf",
        media_type="application/pdf",
    )
    log_lines.extend(["Convert: pdf_ok", "Output: output/main.pdf"])
    return PipelineResult(log_text=format_log(log_lines))


def build_essay_html_prompt(
    *,
    task_text: str,
    context_bundle: str,
    options: dict[str, Any],
    search: dict[str, Any],
) -> tuple[str, str]:
    system_prompt = (
        "You are an expert teaching assistant and cloud engineer writing complete "
        "academic essay and technical report deliverables as self-contained HTML "
        "documents. You write for a university business-analytics course: explain "
        "technical ideas precisely but in plain language, ground every claim in "
        "the student's own evidence, and never invent results. Return only the "
        "requested HTML source, with no surrounding explanation."
    )
    report_instruction = (
        "When the task is a technical or deployment report (for example the "
        "BA3073 assignment 'From AI Agent to Cloud Service'), follow these rules.\n"
        "1. Length and front matter: at most 20 A4 pages. Start with a title, the "
        "student's name and ID if given, course code, date, and a 150-word "
        "executive summary that states the final HTTPS URL and whether each task "
        "succeeded.\n"
        "2. Structure: use numbered sections in this order: (1) Objective and "
        "system architecture; (2) Task 1 local Docker deployment; (3) Revised "
        "report-generation instructions; (4) Task 2 Aliyun ECS deployment via "
        "ACR; (5) Task 3 domain, Nginx reverse proxy, HTTPS and access control; "
        "(6) Security and cost analysis; (7) Problems encountered and fixes; "
        "(8) Improvements and conclusion; then References and an Appendix of "
        "commands and log excerpts.\n"
        "3. Technical explanations: explain how the browser, Nginx, the FastAPI "
        "backend, SQLite, the workspace folder, the Qwen-compatible model API and "
        "Docker relate to each other. Draw the request path as an inline SVG "
        "diagram (browser -> DNS -> Nginx:443 -> 127.0.0.1:14242 container -> "
        "model API). Explain why each step exists: image architecture "
        "(arm64 vs amd64), registry push and pull, volume persistence, port "
        "mapping, security-group rules, TLS certificates, and Basic Auth.\n"
        "4. Evidence: for each task, give the exact commands run, the expected "
        "result, and the observed result. Quote short log excerpts from "
        "local-ui-check.txt and ecs-docker-check.txt (HTTP status, PASS/FAIL, "
        "container status, port mapping) in <pre> blocks. Where the student "
        "provides screenshots, insert a numbered figure placeholder with a "
        "one-sentence caption stating what the screenshot verifies, for example "
        "'Figure 3: ECS UI reached at http://<ip>:14242/ui/ with the address bar "
        "visible.' If evidence is missing, write [EVIDENCE NEEDED: ...] instead "
        "of inventing it.\n"
        "5. Prompt revision section: summarise the original instruction, the "
        "revised instruction, why each change was made, and how the generated "
        "report improved.\n"
        "6. Security and cost: discuss secret handling (API keys never in code, "
        "report or Git), least-privilege security groups, closing public port "
        "14242 after the reverse proxy works, HTTPS, the extra access-control "
        "layer separate from the app's BNBU login, data backups, and the "
        "monthly cost drivers (ECS instance, bandwidth, domain, model tokens).\n"
        "7. Improvements: give concrete, prioritised next steps such as "
        "automatic certificate renewal checks, CI/CD image builds, monitoring and "
        "log rotation, rate limiting, SSO or identity-aware proxies, and "
        "separating SQLite into a managed database.\n"
        "8. Safety: never print API keys, passwords, tokens, private keys or "
        "Basic Auth hashes; replace them with <REDACTED>.\n"
        "9. Style: use short paragraphs, tables for comparisons (for example "
        "local vs ECS vs domain deployment), and consistent terminology. Write "
        "in the language of the assignment task unless the options say otherwise."
    )
    output_instruction = (
        "Return one complete self-contained HTML document. It must start with "
        "<!doctype html> and include <html>, <head>, and <body>. Include all CSS "
        "inside a <style> element: use a readable serif academic print layout, "
        "clear heading hierarchy, careful paragraph spacing, and CSS "
        "@page { size: A4; margin: 20mm; }. Add page-break-inside: avoid to "
        "figures, tables and <pre> blocks, and wrap long commands so they do not "
        "overflow the page. Do not use external stylesheet links, "
        "remote images, or remote HTTP(S) assets. If mathematical notation is "
        "needed, include inline KaTeX-compatible markup and any needed minimal "
        "KaTeX styling inline in the document; do not fetch KaTeX from a CDN at "
        "render time. Use inline SVG or CSS for diagrams. Cite any provided web "
        "sources in a References section using ordinary HTML. Do not wrap the "
        "answer in Markdown fences."
    )
    user_prompt = "\n\n".join(
        [
            "[Assignment Task]\n" + task_text.strip(),
            "[Prepared Context]\n" + context_bundle.strip(),
            "[Search Citations]\n" + format_citations(search),
            "[Options]\n" + json.dumps(options, sort_keys=True),
            "[Report Guidance]\n" + report_instruction,
            "[Output Contract]\n" + output_instruction,
        ]
    )
    return system_prompt, user_prompt
