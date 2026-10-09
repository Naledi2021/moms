import unittest
from unittest.mock import Mock,patch
from design_assistant import api_failure,ask_ai,AIRequestError,validate_proposal

class AIErrorsTests(unittest.TestCase):
    def test_api_failures_are_specific_and_do_not_echo_secrets(self):
        for status,code,expected in ((401,'invalid_api_key','API key'),(429,'insufficient_quota','credit'),(429,'rate_limit_exceeded','rate limit'),(404,'model_not_found','model'),(503,None,'temporarily unavailable')):
            response=Mock(status_code=status);response.json.return_value={'error':{'code':code,'message':'SECRET-DO-NOT-ECHO'}}
            message=api_failure(response)
            self.assertIn(expected,message);self.assertNotIn('SECRET',message)

    def test_ai_request_rejects_quota_safely_and_distinguishes_invalid_proposal(self):
        with patch('design_assistant.requests.post') as post:
            response=post.return_value;response.ok=False;response.status_code=429
            response.json.return_value={'error':{'code':'insufficient_quota'}}
            with self.assertRaisesRegex(AIRequestError,'credit'):ask_ai('kitchen',{},[],[],'fake')
            response.ok=True
            response.json.return_value={'choices':[{'message':{'content':'{"answer":"Hi","units":[{"type":"Unknown"}]}'}}]}
            with self.assertRaisesRegex(AIRequestError,'unsupported'):ask_ai('kitchen',{},[],[],'fake')
            response.json.return_value={'choices':[{'finish_reason':'length','message':{'content':'incomplete'}}]}
            with self.assertRaisesRegex(AIRequestError,'length limit'):ask_ai('kitchen',{},[],[],'fake')

    def test_nullable_optional_placements_are_ignored(self):
        proposal=validate_proposal({'answer':'Review','units':[{'type':'Single door base','wall':None,'x':None}]})
        self.assertNotIn('wall',proposal['units'][0]);self.assertNotIn('x',proposal['units'][0])

if __name__=='__main__':unittest.main()
