class MetadataOnlyBaseline:
    """
    Metadata-only baseline for research question 2.

    It sees ONLY core/application properties (creator, last
    modifier, timestamps, declared application). It cannot see
    RSIDs or revision markup, so it can only ever predict two of
    the four evidence categories:

        - "metadata-only evidence"
        - "no selected edit artifact observed"

    This is a deliberate design assumption: it models an
    investigator who relies on document properties alone. The
    rule-based CorrelationEngine is compared against it on the
    same labelled samples.
    """

    def classify(self, core_properties, app_properties):

        values = list((core_properties or {}).values()) + list(
            (app_properties or {}).values()
        )

        if any(values):
            return {
                "category": "metadata-only evidence",
                "basis": [
                    "At least one selected metadata value was "
                    "present; the baseline does not inspect RSIDs "
                    "or revision markup."
                ],
            }

        return {
            "category": "no selected edit artifact observed",
            "basis": [
                "No selected metadata value was present; the "
                "baseline does not inspect RSIDs or revision "
                "markup."
            ],
        }