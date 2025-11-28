import os
import re
from datetime import datetime

def apply_prompt_template(prompt_name: str, prompt_context={}) -> str:
    """
    템플릿 파일에서 특정 변수만 선택적으로 치환합니다.

    치환 규칙:
    - {VARIABLE_NAME} 형식 (대문자 + 언더스코어 + 숫자)만 치환
    - 다른 패턴의 중괄호는 Python 코드로 간주하여 그대로 유지
    """
    system_prompts = open(os.path.join(os.path.dirname(__file__), f"{prompt_name}.md")).read() ## Template.py가 있는 dir이 기준
    context = {
        "CURRENT_TIME": datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"),
        "COMPANY_NAME": os.getenv("COMPANY_NAME", "YourCompanyName"),
        "INDUSTRY": os.getenv("INDUSTRY", "YourIndustry")
    }
    context.update(prompt_context)

    # 정규식으로 대문자+언더스코어+숫자 패턴만 치환
    def replace_template_variable(match):
        var_name = match.group(1)
        if var_name in context:
            return str(context[var_name])
        else:
            # 컨텍스트에 없으면 원본 유지 (KeyError 방지)
            return match.group(0)

    # 패턴: {대문자_숫자_언더스코어만}
    pattern = r'\{([A-Z_0-9]+)\}'
    system_prompts = re.sub(pattern, replace_template_variable, system_prompts)

    return system_prompts