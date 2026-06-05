import os
import uuid

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from app.utils.logger_config import app_logger as logger

TEMPLATE_DIR = "app/templates"
OUTPUT_DIR = "generated_reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)


env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), auto_reload=True)
env.cache = {}


def render_html(template_name: str, data: dict) -> str:
    logger.debug(f"Rendering HTML template={template_name}")

    template = env.get_template(template_name)
    return template.render(**data)


def _generate_pdf_sync(html_content: str) -> str:
    pdf_filename = f"{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)

    logger.info(f"Generating PDF file={pdf_filename}")

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()

            page.set_content(html_content, wait_until="networkidle")

            page.pdf(
                path=pdf_path,
                format="A4",
                margin={
                    "top": "20mm",
                    "bottom": "20mm",
                    "left": "10mm",
                    "right": "10mm",
                },
                print_background=True,
            )

            browser.close()

        logger.info(f"PDF generated path={pdf_path}")
        return pdf_path

    except Exception:
        logger.exception("PDF generation failed")
        raise


def generate_pdf_from_html(html_content: str) -> str:
    logger.debug("Offloading PDF generation to background thread")
    return _generate_pdf_sync(html_content)
    # return await asyncio.to_thread(_generate_pdf_sync, html_content)
