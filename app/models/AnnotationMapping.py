from app.extensions import db

class AnnotationMapping(db.Model):
    __tablename__ = 'annotation_mappings'

    id = db.Column(db.Integer, primary_key=True)

    annotation_id = db.Column(db.Integer, db.ForeignKey('annotation.id'), nullable=False)
    annotation = db.relationship('Annotation', back_populates='mappings')

    color = db.Column(db.String(7), nullable=False)  # e.g., "#ff0000"
    label = db.Column(db.String(128), nullable=False)  # e.g., "Tumor"

    def serialize(self):
        return {
            "color": self.color,
            "label": self.label
        }