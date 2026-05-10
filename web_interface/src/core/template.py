from jinja2 import Environment, BaseLoader, select_autoescape

class TemplateEngine:
    """Движок рендеринга html
    """

    def __init__(self):
        ...
    
    def render_from_string(self, template: str, context: dict) -> str:
        ...