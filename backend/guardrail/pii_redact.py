from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

_provider = NlpEngineProvider(
    nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_md"}],
    }
)
analyzer = AnalyzerEngine(nlp_engine=_provider.create_engine())
anonymizer = AnonymizerEngine()


if __name__ == "__main__":
    text = """
    My name is John Doe.
    Email: john@gmail.com
    Phone: +1 212-555-5555
    Password : xyz 
    """

    results = analyzer.analyze(
        text=text,
        language="en",
    )

    print(results)

    redacted = anonymizer.anonymize(text=text, analyzer_results=results)

    print(redacted.text)
