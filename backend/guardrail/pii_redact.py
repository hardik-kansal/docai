# from presidio_analyzer import AnalyzerEngine
# from presidio_analyzer.nlp_engine import NlpEngineProvider
# from presidio_anonymizer import AnonymizerEngine


# if __name__ == "__main__":
#     _provider = NlpEngineProvider(
#         nlp_configuration={
#             "nlp_engine_name": "spacy",
#             "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
#         }
#     )
#     analyzer = AnalyzerEngine(nlp_engine=_provider.create_engine())
#     anonymizer = AnonymizerEngine()
#     text = """
#     My name is John Doe.
#     Email: john@gmail.com
#     Phone: +1 212-555-5555
#     Password : xyz
#     """

#     results = analyzer.analyze(
#         text=text,
#         language="en",
#     )

#     print(results)

#     redacted = anonymizer.anonymize(text=text, analyzer_results=results)

#     print(redacted.text)

# # need to add to uv sources
# # en-core-web-sm = { url = "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl" }
