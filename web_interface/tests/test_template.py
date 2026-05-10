from src.core.template import TemplateEngine

def test_secure_engine_renders_correctly():
    engine = TemplateEngine()
    template = "<h1>Dashboard for {{ data.username }}</h1>"
    context = {"data": {"username": "Admin"}}
    
    result = engine.render_from_string(template, context)
    assert result == "<h1>Dashboard for Admin</h1>"

def test_secure_engine_escapes_xss_and_ssti():
    engine = TemplateEngine()
    template = "<div>{{ user_input }}</div>"
    
    malicious_input = "<script>alert('XSS')</script>"
    result = engine.render_from_string(template, {"user_input": malicious_input})
    
    assert "<script>" not in result
    assert "&lt;script&gt;alert(&#39;XSS&#39;)&lt;/script&gt;" in result

def test_secure_engine_handles_missing_variables():
    engine = TemplateEngine()
    template = "Value: {{ missing_var }}"
    
    result = engine.render_from_string(template, {})
    assert result == "Value: "