"""Synthetic evidence tests; no VM, application, or measurement is launched."""
import contextlib
import csv
import io
import json
from pathlib import Path
import sys
import subprocess
import os
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import analyze
from validation import PHASES, sampling_coverage
# analyze adds the legacy module path; pin the iteration comparator explicitly.
sys.path.insert(0, str(ROOT))
import compare


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def run_data(self, name='run', variant='javalin-jdbi3', offset=0):
        root = self.base/name
        (root/'guest').mkdir(parents=True)
        meta = dict(smoke=False,monitored=False,variant=variant,vm='test',guest=name,
                    durations=dict(baseline=30,idle=30,recovery=30),runtime={'boot_id':'boot-'+name})
        (root/'run.json').write_text(json.dumps(meta))
        phases = [dict(phase=n,epoch=t+offset) for n,t in zip(PHASES,[0,30,34,64,364,394])]
        (root/'phases.json').write_text(json.dumps(phases))
        keys = ['epoch','uptime','mem_total_kib','mem_available_kib','swap_used_kib','pswpin_pages','pswpout_pages',
                'cpu_total_ticks','cpu_idle_ticks','cpu_iowait_ticks','cpu_steal_ticks','java_pid','java_rss_kib','java_swap_kib',
                'java_threads','java_cpu_ticks','monitor_pid','monitor_rss_kib','monitor_swap_kib','monitor_cpu_ticks',
                'host_major_faults','java_major_faults']
        with (root/'guest/os.csv').open('w') as out:
            writer=csv.DictWriter(out,fieldnames=keys);writer.writeheader()
            for t in sorted(set(range(0,30,5)) | set(range(30,34)) | set(range(34,394,5))):
                row=dict.fromkeys(keys,0)
                row.update(epoch=t+offset,uptime=t,mem_total_kib=477712,mem_available_kib=280000,
                           cpu_total_ticks=t*100,cpu_idle_ticks=t*75,java_pid=100,java_rss_kib=100000,
                           java_cpu_ticks=t*20,java_threads=15)
                writer.writerow(row)
        events=[dict(index=i,route='batch' if i%5==4 else 'latest',ok=True,status=201 if i%5==4 else 200,
                     completed_epoch=64+offset+i*.2,latency_ms=5,lag_ms=0) for i in range(1500)]
        (root/'http.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
        (root/'db-state.json').write_text(json.dumps(dict(status=200,body=dict(rows=2070,maxSequence=689,priceSum='630374.22'))))
        import datetime
        (root/'java-launch-utc.txt').write_text(datetime.datetime.fromtimestamp(30+offset,datetime.timezone.utc).isoformat())
        (root/'probes.json').write_text(json.dumps([dict(epoch=34+offset,status=200)]))
        preparation=self.base/'preparation.json'
        preparation.write_text(json.dumps(dict(source_commit='test',application_jars={'app':'same'},versions={'jdk':'25'},jvm_flags=['test'],vm={'cpus':1})))
        meta['preparation']='../preparation.json'
        (root/'run.json').write_text(json.dumps(meta))
        return root

    def analysis(self,root):
        with contextlib.redirect_stdout(io.StringIO()):
            return analyze.analyze(root)

    def fail_batch(self,root,index):
        events=[json.loads(line) for line in (root/'http.jsonl').read_text().splitlines()]
        events[index].update(ok=False,status=500)
        (root/'http.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
        with (analyze.workload.ROOT/'common/src/main/resources/quotes.csv').open() as source:
            fixture_rows=list(csv.DictReader(source))
        fixture=[{'prices':{r['symbol']:r['price'] for r in fixture_rows[i:i+3]}} for i in range(0,len(fixture_rows),3)]
        _,state=analyze.workload_and_state(dict(smoke=False),events,None,fixture)
        body=state['acknowledged_writes_expected']
        (root/'db-state.json').write_text(json.dumps(dict(status=200,body=body)))

    def test_complete_run(self):
        self.assertTrue(self.analysis(self.run_data())['validity']['valid_for_comparison'])

    def test_failed_final_and_intermediate_batches(self):
        for i in [1499,504]:
            with self.subTest(index=i):
                root=self.run_data(str(i));self.fail_batch(root,i);result=self.analysis(root)
                self.assertFalse(result['validity']['valid_for_comparison'])
                self.assertFalse(result['persistence_state']['matches'])
                self.assertTrue(result['persistence_state']['matches_acknowledged_writes'])

    def test_missing_request_even_with_fixed_state(self):
        root=self.run_data();p=root/'http.jsonl';p.write_text('\n'.join(p.read_text().splitlines()[:-1])+'\n')
        self.assertTrue(self.analysis(root)['persistence_state']['matches'])
        self.assertFalse(self.analysis(root)['validity']['valid_for_comparison'])

    def test_truncated_and_gapped_and_empty_sampling(self):
        for kind in ['truncated','gapped','empty']:
            root=self.run_data(kind);p=root/'guest/os.csv';lines=p.read_text().splitlines()
            if kind=='truncated': lines=lines[:1]+[line for line in lines[1:] if float(line.split(',')[0])<100]
            elif kind=='gapped': lines=lines[:1]+[line for line in lines[1:] if not 100<float(line.split(',')[0])<140]
            else: lines=lines[:1]
            p.write_text('\n'.join(lines)+'\n')
            result=self.analysis(root)
            self.assertFalse(result['sampling_coverage']['valid'])
            self.assertFalse(result['validity']['valid_for_comparison'])

    def test_offset_cadence_transitions(self):
        phases=[dict(phase=n,epoch=t) for n,t in zip(PHASES,[0,30,34,64,364,394])]
        times=([t+.2 for t in range(0,30,5)] + [30.3,31.3,32.3,33.3]
               + [t+.3 for t in range(34,394,5)])
        result=sampling_coverage(dict(smoke=False,monitored=False),phases,[{'epoch':t} for t in times])
        self.assertTrue(result['valid'],result['issues'])
        # Removing genuine startup evidence must still fail.
        result=sampling_coverage(dict(smoke=False,monitored=False),phases,
                                 [{'epoch':t} for t in times if not 30<=t<34])
        self.assertFalse(result['valid'])

    def test_run_order_and_boot_ids(self):
        roots=[self.run_data(str(i),v,offset=i*400)
               for i,v in enumerate(compare.VARIANTS+list(reversed(compare.VARIANTS)))]
        # Input argument order is irrelevant; chronology is authoritative.
        self.assertTrue(compare.compare(list(reversed(roots)))['complete'])
        for index,variant in enumerate(compare.VARIANTS*2):
            p=roots[index]/'run.json';meta=json.loads(p.read_text());meta['variant']=variant;p.write_text(json.dumps(meta))
        self.assertIn('Chronological', ' '.join(compare.compare(roots)['issues']))
        for index,variant in enumerate(compare.VARIANTS+list(reversed(compare.VARIANTS))):
            p=roots[index]/'run.json';meta=json.loads(p.read_text());meta['variant']=variant;p.write_text(json.dumps(meta))
        p=roots[-1]/'run.json';meta=json.loads(p.read_text())
        for boot in ['boot-0',None]:
            meta['runtime']['boot_id']=boot;p.write_text(json.dumps(meta))
            self.assertIn('boot ID', ' '.join(compare.compare(roots)['issues']))

    def test_shutdown_requires_jvm_exit(self):
        # Simulate /proc and sleep only: execute the production stop-java branch
        # without creating/killing processes or waiting thirty real seconds.
        proc=self.base/'proc';(proc/'1234').mkdir(parents=True)
        status=proc/'1234/status'
        run=self.base/'shutdown';run.mkdir();(run/'java.pid').write_text('1234')
        script=self.base/'guest.sh'
        script.write_text((ROOT/'guest.sh').read_text().replace('/proc/',str(proc)+'/'))
        waits=self.base/'waits'
        env=dict(os.environ,WAIT_LOG=str(waits))
        command=['bash','-c',
                 'kill(){ :; }; sleep(){ echo wait >> "$WAIT_LOG"; }; export -f kill sleep; exec bash "$@"',
                 'test',str(script),'stop-java','javalin-jdbi3',str(run),str(self.base)]
        status.write_text('State: S (sleeping)\n')
        result=subprocess.run(command,capture_output=True,text=True,env=env)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('shutdown timed out',result.stderr)
        self.assertEqual(len(waits.read_text().splitlines()),30)
        status.write_text('State: Z (zombie)\n')
        self.assertEqual(subprocess.run(command,capture_output=True,env=env).returncode,0)
        status.unlink()
        self.assertEqual(subprocess.run(command,capture_output=True,env=env).returncode,0)

    def test_matrix_and_configuration_and_duplicates(self):
        roots=[self.run_data(str(i),v,offset=i*400) for i,v in enumerate(compare.VARIANTS+list(reversed(compare.VARIANTS)))]
        self.assertTrue(compare.compare(roots)['complete'])
        self.assertFalse(compare.compare(roots[:1])['complete'])
        self.assertEqual(compare.compare(roots[:1])['unmonitored_ranges'],{})
        self.assertFalse(compare.compare(roots[:-1]+roots[:1])['complete'])
        p=roots[0]/'run.json';meta=json.loads(p.read_text());meta['durations']['idle']=31;p.write_text(json.dumps(meta))
        self.assertFalse(compare.compare(roots)['complete'])
        meta['durations']['idle']=30;p.write_text(json.dumps(meta))
        self.fail_batch(roots[0],1499)
        self.assertFalse(compare.compare(roots)['complete'])

    def test_one_page_memory_variation(self):
        roots=[self.run_data(str(i),v,offset=i*400)
               for i,v in enumerate(compare.VARIANTS+list(reversed(compare.VARIANTS)))]
        for root in roots:
            p=root/'run.json';meta=json.loads(p.read_text())
            meta['runtime']['mem_total_kib']=477712;p.write_text(json.dumps(meta))
        p=roots[-1]/'guest/os.csv';original=p.read_text()
        meta_path=roots[-1]/'run.json';meta=json.loads(meta_path.read_text())
        for memory,accepted in [(477708,True),(477704,False),(450000,False)]:
            p.write_text(original.replace('477712',str(memory)))
            meta['runtime']['mem_total_kib']=memory;meta_path.write_text(json.dumps(meta))
            result=compare.compare(roots)
            self.assertEqual(result['complete'],accepted,result['issues'])
            self.assertEqual(result['runs'][-1]['actual_mem_mib'],memory/1024)


if __name__=='__main__':
    unittest.main()
