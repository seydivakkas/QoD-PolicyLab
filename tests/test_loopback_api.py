import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from qodpolicylab.api import dispatch, server

class APIContractTests(unittest.TestCase):
    def test_simulator_and_pareto(self):
        cfg={'duration_s':2.,'static_threshold':0.}
        result=dispatch({'schema_version':'1.0','operation':'simulate','input':{'config':cfg,'policy':'static'}})
        self.assertEqual(result['policy'],'static')
        self.assertEqual(result['model'],'hypothetical QoD; not actual 5G service')
        cmp=dispatch({'schema_version':'1.0','operation':'compare','input':{'config':cfg,'seeds':3}})
        self.assertIn('pareto_frontier',cmp)
        with self.assertRaises(ValueError):dispatch({'schema_version':'1.0','operation':'compare','input':{'config':cfg,'seeds':51}})

    def test_loopback_token_and_reject_browser_origin(self):
        server_instance=server(token='Q'*30,port=0)
        worker=threading.Thread(target=server_instance.serve_forever,daemon=True)
        worker.start()
        url=f'http://127.0.0.1:{server_instance.server_address[1]}'
        data=json.dumps({'schema_version':'1.0','operation':'simulate','input':{'config':{'duration_s':1.},'policy':'static'}}).encode()
        try:
            req=Request(url+'/v1/execute',data=data,headers={'Authorization':'Bearer '+'Q'*30,'Content-Type':'application/json'},method='POST')
            value=json.load(urlopen(req,timeout=2))
            self.assertIn('deadline_miss_rate',value['result'])
            evil=Request(url+'/v1/execute',data=data,headers={'Authorization':'Bearer '+'Q'*30,'Content-Type':'application/json','Origin':'null'},method='POST')
            with self.assertRaises(HTTPError) as e:urlopen(evil,timeout=2)
            self.assertEqual(e.exception.code,403)
        finally:
            server_instance.shutdown();server_instance.server_close();worker.join(timeout=2)

if __name__=='__main__':unittest.main()