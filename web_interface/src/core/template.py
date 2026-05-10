from jinja2 import Environment, BaseLoader, select_autoescape

class TemplateEngine:
    """Движок рендеринга html
    """

    def __init__(self):
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=select_autoescape(['html', 'xml'])
        )
    
    def render_from_string(self, template: str, context: dict) -> str:
        """Рендерит строку шаблона с переданным контекстом

        Args:
            template (str): HTML-разметка шаблона
            context (dict): Словарь с данными для подстановки

        Returns:
            str: Готовый HTML код
        """
        template = self.env.from_string(template)
        return template.render(**context)

engine = TemplateEngine()
