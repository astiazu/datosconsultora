# preflight.py
import re

def check(path, pattern, expect=True):
    try:
        with open(path, encoding="utf-8") as f:
            found = re.search(pattern, f.read()) is not None
    except FileNotFoundError:
        found = False
    ok = (found == expect)
    print(f"{'OK ' if ok else 'FALTA'} | {path} | esperaba {'True' if expect else 'False'} y dio {found}")

check("app/services/plan_service.py", r"LIMITES_COMENTARIOS_POR_PLAN")
check("app/mic/providers/model_config.py", r'"plata":\s*"qwen-2\.5-32b"')
check("app/services/analysis_service.py", r"limite_comentarios")
check("app/mic/providers/base.py", r"limite_comentarios")
check("app/mic/providers/groq_provider.py", r"limite_comentarios")
check("app/services/analysis/groq_llm.py", r"limite_comentarios")
check("app/mic/analyzers/groq_semantic_analyzer.py", r"limite_comentarios")
check("app/services/plata/semantic_service.py", r"limite_comentarios")
check("app/templates/analisis_sentimientos.html", r"recuperá TODOS")
check("app/services/scraper_service.py", r"comentarios_unicos\[:100\]", expect=False)
check("app/routes/servicios.py", r"limite_comentarios_para_plan")
print("\nListo. Si todo dice OK, pasá a las pruebas reales.")