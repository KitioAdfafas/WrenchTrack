MAX_AMOUNT = 100000
MAX_QUANTITY = 1000
MAX_PART_NAME = 100
MAX_PHOTO_NAME = 100
MAX_CODE = 20
MAX_DESCRIPTION = 200

def init_app(app):
    """Make every limit usable in templates under the same name."""
    app.add_template_global(MAX_AMOUNT, "MAX_AMOUNT")
    app.add_template_global(MAX_QUANTITY, "MAX_QUANTITY")
    app.add_template_global(MAX_PART_NAME, "MAX_PART_NAME")
    app.add_template_global(MAX_PHOTO_NAME, "MAX_PHOTO_NAME")
    app.add_template_global(MAX_CODE, "MAX_CODE")
    app.add_template_global(MAX_DESCRIPTION, "MAX_DESCRIPTION")
