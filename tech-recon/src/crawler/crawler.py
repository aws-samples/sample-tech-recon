import sys
import requests
from bs4 import BeautifulSoup
from .article import Article

class Crawler:
    def __init__(self, timeout=30):
        """
        Initialize Crawler with configurable timeout.

        Args:
            timeout: Request timeout in seconds (default: 30)
        """
        self.timeout = timeout

    def crawl(self, url: str) -> Article:
        # 브라우저처럼 보이는 사용자 에이전트 설정
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        print(f"🔍 Crawling URL: {url} (timeout: {self.timeout}s)")

        # requests를 사용하여 웹 페이지 가져오기 (타임아웃 설정 추가)
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()  # 오류 발생 시 예외 발생
            print(f"✅ Response received: {response.status_code} ({len(response.content)} bytes)")
        except requests.Timeout:
            raise Exception(f"Request timeout after {self.timeout} seconds")
        except requests.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
        
        # BeautifulSoup을 사용하여 HTML 파싱
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # 주요 콘텐츠 추출 - 다양한 선택자 시도
        title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"

        # 본문 추출 - 여러 선택자 시도 (우선순위 순)
        content = ""
        content_selectors = [
            soup.find('article'),
            soup.find('main'),
            soup.find('div', class_='content'),
            soup.find('div', class_='article'),
            soup.find('div', class_='post'),
            soup.find('div', id='content'),
            soup.find('div', id='main'),
            soup.body  # 최후의 수단
        ]

        main_content = None
        for selector in content_selectors:
            if selector:
                main_content = selector
                break

        if main_content:
            # Extract all text content with better formatting
            # Get all paragraphs, headings, and list items
            text_elements = []

            # Headings
            for heading in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = heading.get_text().strip()
                if text:
                    text_elements.append(f"\n## {text}\n")

            # Paragraphs
            for p in main_content.find_all('p'):
                text = p.get_text().strip()
                if text and len(text) > 20:  # Filter out very short paragraphs
                    text_elements.append(text)

            # List items
            for li in main_content.find_all('li'):
                text = li.get_text().strip()
                if text:
                    text_elements.append(f"- {text}")

            content = '\n\n'.join(text_elements)

        # Fallback: if content is still empty, get all text
        if not content or len(content) < 100:
            content = soup.get_text(separator='\n', strip=True)
            # Clean up multiple newlines
            content = '\n'.join([line for line in content.split('\n') if line.strip()])

        print(f"📄 Extracted: title='{title[:50]}...', content={len(content)} chars")
        
        # Article 객체 생성 및 반환
        article = Article(
            title=title,
            html_content=content
        )
        #article.url = url
        #article.title = title
        #article.html_content = content
        #article.images = images
        
        return article

if __name__ == "__main__":
    if len(sys.argv) == 2:
        url = sys.argv[1]
    else:
        url = "https://fintel.io/zh-hant/s/br/nvdc34"
    crawler = Crawler()
    article = crawler.crawl(url)
    print(article.to_markdown())