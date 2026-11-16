from pathlib import Path
import hashlib,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from finagent_googl_xml_alias_v2 import canonical_markup
class MarkupGuards(unittest.TestCase):
    def setUp(self):
        self.text='```xml\n<output>\n<analysis>Do not drop eBay or any other word.\n</analysis>\n<summary>Hold the same text & punctuation.</summary>\n</output>\n```'
        self.normal=self.text.replace('<analysis>','<string name="analysis">').replace('</analysis>','</string>').replace('<summary>','<string name="summary">').replace('</summary>','</string>')
        self.w={'request_hash':'key','response_sha256':hashlib.sha256(self.text.encode()).hexdigest(),'normalized_response_sha256':hashlib.sha256(self.normal.encode()).hexdigest()}
    def test_exact_markup_only(self):self.assertEqual(canonical_markup(self.text,'key',self.w),(self.normal,True))
    def test_unrelated_key_unchanged(self):self.assertEqual(canonical_markup(self.text,'other',self.w),(self.text,False))
    def test_altered_word_refused(self):
        with self.assertRaises(ValueError):canonical_markup(self.text.replace('eBay','Alphabet'),'key',self.w)
    def test_altered_whitespace_refused(self):
        with self.assertRaises(ValueError):canonical_markup(self.text+' ','key',self.w)
    def test_wrong_canonical_digest_refused(self):
        self.w['normalized_response_sha256']='0'*64
        with self.assertRaises(ValueError):canonical_markup(self.text,'key',self.w)
    def test_duplicate_field_refused_even_if_hash_matches(self):
        value=self.text.replace('</output>','<analysis>extra</analysis></output>');self.w['response_sha256']=hashlib.sha256(value.encode()).hexdigest()
        with self.assertRaises(ValueError):canonical_markup(value,'key',self.w)
    def test_missing_field_not_invented(self):
        value=self.text.replace('<summary>Hold the same text & punctuation.</summary>','');self.w['response_sha256']=hashlib.sha256(value.encode()).hexdigest()
        with self.assertRaises(ValueError):canonical_markup(value,'key',self.w)
    def test_already_named_unrelated_response_unchanged(self):self.assertEqual(canonical_markup(self.normal,'other',self.w),(self.normal,False))
if __name__=='__main__':unittest.main()
