import unittest
from src.models import CanonicalProfile, Location, Skill, Links
from src.projection import project_profile
from src.validation import validate_projected_output

class TestProjection(unittest.TestCase):
    def setUp(self):
        self.profile = CanonicalProfile(
            candidate_id="rohan",
            full_name="Rohan Pagadala",
            emails=["rohan.pagadala15@gmail.com", "rohan@eightfold.ai"],
            phones=["+919876543210"],
            location=Location(city="Hyderabad", region="TG", country="IN"),
            links=Links(linkedin="https://linkedin.com/in/rohanpagadala"),
            skills=[
                Skill(name="Python", confidence=1.0, sources=["resume.txt"]),
                Skill(name="Machine Learning", confidence=0.8, sources=["linkedin.json"])
            ],
            overall_confidence=0.9
        )

    def test_basic_projection(self):
        config = {
            "fields": [
                { "path": "full_name", "type": "string", "required": True },
                { "path": "primary_email", "from": "emails[0]", "type": "string", "required": True },
                { "path": "skills", "from": "skills[].name", "type": "string[]" }
            ],
            "include_confidence": True,
            "on_missing": "null"
        }
        
        projected = project_profile(self.profile, config)
        
        self.assertEqual(projected["full_name"], "Rohan Pagadala")
        self.assertEqual(projected["primary_email"], "rohan.pagadala15@gmail.com")
        self.assertEqual(projected["skills"], ["Python", "Machine Learning"])
        self.assertEqual(projected["overall_confidence"], 0.9)

        # Validate projected output
        validated = validate_projected_output(projected, config)
        self.assertEqual(validated["full_name"], "Rohan Pagadala")

    def test_missing_on_missing_omit(self):
        config = {
            "fields": [
                { "path": "full_name", "type": "string", "required": True },
                { "path": "headline", "type": "string" } # headline is missing on profile
            ],
            "include_confidence": False,
            "on_missing": "omit"
        }
        
        projected = project_profile(self.profile, config)
        self.assertEqual(projected["full_name"], "Rohan Pagadala")
        self.assertNotIn("headline", projected)

    def test_missing_on_missing_error(self):
        config = {
            "fields": [
                { "path": "full_name", "type": "string", "required": True },
                { "path": "headline", "type": "string" }
            ],
            "on_missing": "error"
        }
        
        with self.assertRaises(ValueError):
            project_profile(self.profile, config)

    def test_validation_error_dynamic_schema(self):
        config = {
            "fields": [
                { "path": "full_name", "type": "string", "required": True },
                { "path": "primary_email", "from": "emails[0]", "type": "string", "required": True }
            ]
        }
        
        # Tamper with projected output to cause validation error
        bad_projected = {
            "full_name": 12345,  # Should be string
            "primary_email": "rohan.pagadala15@gmail.com"
        }
        
        with self.assertRaises(ValueError):
            validate_projected_output(bad_projected, config)

if __name__ == "__main__":
    unittest.main()
