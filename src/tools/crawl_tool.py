import logging
from typing import Any, Annotated
from strands.types.tools import ToolResult, ToolUse
from src.tools.decorators import log_io
from src.crawler import Crawler

# 새 핸들러와 포맷터 설정
logger = logging.getLogger(__name__)
logger.propagate = False  # 상위 로거로 메시지 전파 중지
for handler in logger.handlers[:]:
    logger.removeHandler(handler)
handler = logging.StreamHandler()
formatter = logging.Formatter('\n%(levelname)s [%(name)s] %(message)s')  # 로그 레벨이 동적으로 표시되도록 변경
handler.setFormatter(formatter)
logger.addHandler(handler)
# DEBUG와 INFO 중 원하는 레벨로 설정
logger.setLevel(logging.INFO)  # 기본 레벨은 INFO로 설정

TOOL_SPEC = {
    "name": "crawl_tool",
    "description": "Use this to crawl a url and get a readable content in markdown format.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The url to crawl."
                }
            },
            "required": ["url"]
        }
    }
}

class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# Initialize crawler instance with 30 second timeout
crawler = Crawler(timeout=30)

@log_io
def handle_crawl_tool(url: Annotated[str, "The url to crawl."]) -> str:
    """
    Use this to crawl a url and get a readable content in markdown format.
    """
    logger.info(f"{Colors.BLUE}===== Crawling URL: {url} ====={Colors.END}")
    try:
        # Crawl the URL
        article = crawler.crawl(url)

        # Get the message content
        content = article.to_message()[-1]["text"]

        # Log success with content length
        content_length = len(content)
        logger.info(f"{Colors.GREEN}===== Crawling successful ({content_length} chars) ====={Colors.END}")

        # Return with more informative message
        result = f"""Successfully crawled URL: {url}

Title: {article.title if hasattr(article, 'title') else 'N/A'}
Content length: {content_length} characters

Content:
{content}"""

        return result

    except Exception as e:
        error_msg = f"Failed to crawl URL: {url}\nError: {repr(e)}\n\nTip: The URL might be blocking automated requests, timing out, or have parsing issues. Try a different URL or skip this source."
        logger.error(f"{Colors.RED}Crawling failed: {repr(e)}{Colors.END}")
        return error_msg

# Function name must match tool name
def crawl_tool(tool: ToolUse, **kwargs: Any) -> ToolResult:
    tool_use_id = tool["toolUseId"]
    url = tool["input"]["url"]
    
    # Use the existing handle_crawl_tool function
    result = handle_crawl_tool(url)
    
    # Check if crawling was successful based on the result string
    if "Failed to crawl" in result:
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": result}]
        }
    else:
        return {
            "toolUseId": tool_use_id,
            "status": "success",
            "content": [{"text": result}]
        }