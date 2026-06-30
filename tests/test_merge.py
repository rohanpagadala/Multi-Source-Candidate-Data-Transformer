import unittest
from src.models import RawFact
from src.merge import cluster_facts_by_candidate, merge_candidate_facts

class TestMerge(unittest.TestCase):
    def test_clustering_by_email(self):
        facts = [
            RawFact(field="full_name", value="Rohan P", source="resume.txt", method="test"),
            RawFact(field="email", value="rohan.pagadala15@gmail.com", source="resume.txt", method="test"),
            RawFact(field="full_name", value="Rohan Pagadala", source="linkedin.json", method="test"),
            RawFact(field="email", value="rohan.pagadala15@gmail.com", source="linkedin.json", method="test"),
            
            # Another candidate
            RawFact(field="full_name", value="John Doe", source="ats.json", method="test"),
            RawFact(field="email", value="john.doe@example.com", source="ats.json", method="test")
        ]
        
        clusters = cluster_facts_by_candidate(facts)
        self.assertEqual(len(clusters), 2)
        
        # Check that Rohan P and Rohan Pagadala are clustered together
        rohan_cluster = next(c for c in clusters if any(f.value == "rohan.pagadala15@gmail.com" for f in c))
        self.assertEqual(len({f.source for f in rohan_cluster}), 2) # resume.txt and linkedin.json

    def test_clustering_by_name_fallback(self):
        # Rohan has no contact info in resume.txt but matches linkedin by name
        facts = [
            RawFact(field="full_name", value="Rohan Pagadala", source="resume.txt", method="test"),
            # No email/phone in resume
            
            RawFact(field="full_name", value="Rohan Pagadala", source="linkedin.json", method="test"),
            RawFact(field="email", value="rohan.pagadala15@gmail.com", source="linkedin.json", method="test")
        ]
        
        clusters = cluster_facts_by_candidate(facts)
        self.assertEqual(len(clusters), 1)

    def test_conflict_resolution_priority(self):
        facts = [
            # Resume has priority 3 (High)
            RawFact(field="full_name", value="Rohan Pagadala (Resume)", source="resume.txt", method="test", confidence=1.0),
            # Notes has priority 1 (Low)
            RawFact(field="full_name", value="Rohan P (Notes)", source="recruiter_notes.txt", method="test", confidence=1.0)
        ]
        
        profile = merge_candidate_facts(facts)
        # Winner must be from Resume
        self.assertEqual(profile.full_name, "Rohan Pagadala (Resume)")
        
        # Provenance must record both entries, with Notes discounted
        prov_fields = [p.field for p in profile.provenance]
        self.assertIn("full_name", prov_fields)
        self.assertEqual(len(profile.provenance), 2)
        
        notes_prov = next(p for p in profile.provenance if p.value == "Rohan P (Notes)")
        # Original conf was 1.0, discounted should be 0.7
        self.assertAlmostEqual(notes_prov.confidence, 0.7)

if __name__ == "__main__":
    unittest.main()
