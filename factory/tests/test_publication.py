"""Publication regressions over real Git indexes, commits, tags and pushes."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tarfile
import unittest
import zipfile
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gatekeeper as g
from engine import publication as p
from engine.io import EvidenceError,read_json,write_json


@unittest.skipUnless(shutil.which('git'),'Git unavailable')
class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='publication-test-')
        self.root=Path(self.temp.name)/'work';self.root.mkdir()
        self.environment=os.environ.copy()
        for key in list(self.environment):
            if key.startswith('GIT_'):self.environment.pop(key)
        self.environment.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,
                                GIT_TERMINAL_PROMPT='0',PYTHONDONTWRITEBYTECODE='1')
        self.env_patch=patch.dict(os.environ,self.environment,clear=True);self.env_patch.start()
        p.initialize(self.root)
        self.git('config','user.name','Project Developer')
        self.git('config','user.email','developer@example.test')
        self.git('symbolic-ref','HEAD','refs/heads/main')
        self.git('add','.gitignore')

    def tearDown(self):
        self.env_patch.stop();self.temp.cleanup()

    def git(self,*args,ok=True):
        result=subprocess.run(['git','-C',str(self.root),*args],capture_output=True,env=self.environment)
        if ok:self.assertEqual(result.returncode,0,result.stderr.decode())
        return result

    def add(self,name,text,force=False):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(text if isinstance(text,bytes) else text.encode())
        self.git('add',*(['-f'] if force else []),name)
        return path

    def codes(self,**kwargs):return {x['code'] for x in p.check(self.root,**kwargs)['errors']}

    def commit(self,message='Add prediction evaluator',bypass=False):
        return self.git(*(['-c','core.hooksPath=/dev/null'] if bypass else []),'commit','-m',message,ok=not bypass)

    def remote(self):
        bare=Path(self.temp.name)/'remote.git'
        result=subprocess.run(['git','init','--bare',str(bare)],capture_output=True,env=self.environment)
        self.assertEqual(result.returncode,0)
        self.git('remote','add','origin',str(bare));return bare

    def test_neutral_ignore_and_private_state(self):
        ignore=(self.root/'.gitignore').read_text()
        self.assertFalse(p._text_findings(ignore,'.gitignore'))
        for name in ['factory/a.py','project/research_plan.json','TAKE_THIS/a.zip','DROP_HERE/a','AGENTS.md']:
            self.assertEqual(self.git('check-ignore',name).returncode,0)
        self.assertEqual(p.check(self.root)['status'],'PASS')
        tracked=self.git('ls-files').stdout.decode()
        self.assertEqual(tracked,'.gitignore\n')

    def test_force_added_internal_file_is_blocked(self):
        self.add('factory/innocent.txt','local rules',force=True)
        self.assertIn('NON_PROJECT_PATH',self.codes())
        self.assertNotEqual(self.git('commit','-m','Add evaluator',ok=False).returncode,0)

    def test_non_project_root_and_nested_private_paths(self):
        for name in ('report.md','src/.factory/key','docs/architect_spec.md','src/.env'):
            with self.subTest(name=name):
                self.add(name,'private',force=True)
                self.assertIn('NON_PROJECT_PATH',self.codes())
                self.git('rm','--cached',name)

    def test_comments_docs_notebooks_and_ci_are_scanned(self):
        for name in ('source/main.py','docs/methods.md','notebooks/study.ipynb','.github/workflows/check.yml'):
            with self.subTest(name=name):
                self.add(name,'# Validated by software-factory gatekeeper.py\n')
                self.assertIn('INTERNAL_FRAMEWORK',self.codes())
                self.git('rm','--cached',name)

    def test_professional_domain_factory_term_is_allowed(self):
        self.add('source/main.py','def factory():\n    """Create a prediction model."""\n    return object()\n')
        self.assertEqual(p.check(self.root)['status'],'PASS')
        self.commit('Add model factory and validation routines')

    def test_staged_leak_cannot_hide_behind_clean_worktree(self):
        path=self.add('source/main.py','# gatekeeper.py\n')
        path.write_text('# Evaluate held-out predictions.\n')
        self.assertIn('INTERNAL_FRAMEWORK',self.codes())

    def test_unstaged_changes_do_not_substitute_for_staged_bytes(self):
        path=self.add('source/main.py','# Evaluate held-out predictions.\n')
        path.write_text('# gatekeeper.py\n')
        self.assertEqual(p.check(self.root)['status'],'PASS')
        self.commit()
        self.assertEqual(p.check(self.root,refs=['HEAD'])['status'],'PASS')

    def test_commit_messages_are_checked_by_real_hook(self):
        self.add('source/main.py','print("ready")\n')
        result=self.git('commit','-m','Pass the software-factory gate',ok=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn(b'INTERNAL_FRAMEWORK',result.stderr)
        self.commit('Add result validation')

    def test_generated_assistant_trailer_is_blocked_by_real_hook(self):
        self.add('source/main.py','print("ready")\n')
        result=self.git('commit','-m','Add evaluator\n\nCo-authored-by: Claude <noreply@anthropic.com>',ok=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn(b'TOOL_NARRATION',result.stderr)
        self.commit('Add evaluator')

    def test_outgoing_history_checks_deleted_leaks(self):
        self.add('source/main.py','# gatekeeper.py\n')
        self.assertEqual(self.commit('Add evaluator',bypass=True).returncode,0)
        self.add('source/main.py','# Evaluate predictions.\n');self.commit('Improve evaluator')
        report=p.check(self.root,refs=['HEAD'])
        self.assertEqual(report['status'],'BLOCKED')
        self.assertEqual(report['commits_checked'],2)
        self.remote()
        self.assertNotEqual(self.git('push','origin','main',ok=False).returncode,0)

    def test_actual_clean_commit_and_push(self):
        self.add('source/main.py','# Evaluate predictions.\n');self.commit()
        self.remote();self.git('push','origin','main')
        self.assertEqual(p.check(self.root,refs=p.current_refs(self.root))['status'],'PASS')

    def test_old_commit_message_blocks_push(self):
        self.add('source/main.py','print("ready")\n')
        self.assertEqual(self.commit('Generated by Claude',bypass=True).returncode,0)
        self.assertIn('TOOL_NARRATION',self.codes(refs=['HEAD']))
        self.remote();self.assertNotEqual(self.git('push','origin','main',ok=False).returncode,0)

    def test_annotated_tag_message_cannot_leak(self):
        self.commit();self.git('tag','-a','v1','-m','Pass software-factory rules')
        self.assertIn('INTERNAL_FRAMEWORK',self.codes(refs=['refs/tags/v1']))
        self.remote();self.assertNotEqual(self.git('push','origin','v1',ok=False).returncode,0)

    def test_tag_to_uninspected_blob_is_blocked(self):
        self.commit();oid=self.git('rev-parse','HEAD:.gitignore').stdout.decode().strip()
        self.git('tag','document',oid)
        self.assertIn('UNINSPECTED_REF',self.codes(refs=['document']))

    def test_internal_ref_names_are_blocked(self):
        self.commit();self.remote()
        self.assertNotEqual(self.git('push','origin','main:refs/heads/codex/fix',ok=False).returncode,0)
        self.git('checkout','-b','factory-fix')
        self.assertIn('INTERNAL_REF_NAME',self.codes())

    def test_credential_in_ref_is_blocked_without_echoing_it(self):
        self.commit();secret='ghp_'+'A'*36
        self.git('checkout','-b','codex/'+secret)
        report=p.check(self.root,refs=p.current_refs(self.root))
        self.assertIn('ACCESS_TOKEN',{entry['code'] for entry in report['errors']})
        self.assertNotIn(secret,json.dumps(report))
        self.remote();result=self.git('push','origin','HEAD:refs/heads/public',ok=False)
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn(secret,result.stderr.decode())

    def test_credentials_in_commit_author_metadata_are_blocked(self):
        self.git('config','user.name','ghp_'+'A'*36)
        self.assertEqual(self.commit(bypass=True).returncode,0)
        self.assertIn('ACCESS_TOKEN',self.codes(refs=['HEAD']))

    def test_renamed_archive_is_not_public_data(self):
        archive=self.root/'data/results.bin';archive.parent.mkdir()
        with zipfile.ZipFile(archive,'w') as bundle:bundle.writestr('factory/notes.md','internal procedures')
        self.git('add','data/results.bin')
        self.assertIn('PUBLIC_ARCHIVE',self.codes())

    def test_renamed_tar_and_compression_cannot_hide_private_files(self):
        archive=self.root/'data/study.bin';archive.parent.mkdir()
        with tarfile.open(archive,'w') as bundle:
            entry=tarfile.TarInfo('private.txt');entry.size=7
            bundle.addfile(entry,io.BytesIO(b'private'))
        self.git('add','data/study.bin')
        self.assertIn('PUBLIC_ARCHIVE',self.codes())
        for header in (b'\x1f\x8b',b'BZh',b'\xfd7zXZ\x00',b'PK\x05\x06'):
            self.add('data/study.bin',header+b'private')
            self.assertIn('PUBLIC_ARCHIVE',self.codes())

    def test_lfs_pointer_cannot_hide_uninspected_artifact(self):
        self.add('data/study.bin','version https://git-lfs.github.com/spec/v1\noid sha256:'+('a'*64)+'\nsize 2048\n')
        self.assertIn('UNINSPECTED_EXTERNAL_ARTIFACT',self.codes())

    def test_binary_metadata_is_checked_despite_hash_approval(self):
        raw=b'\x89PNG\x00\xffsoftware-factory review instructions'
        self.add('figures/result.png',raw)
        policy=p.load_policy(self.root)
        policy['approved_binary_artifacts']['figures/result.png']={
            'sha256':hashlib.sha256(raw).hexdigest(),'reason':'Inspected project figure for scientific release.'}
        write_json(self.root/p.POLICY,policy)
        self.assertIn('INTERNAL_FRAMEWORK',self.codes())

    def test_force_added_cache_and_credentials_are_private(self):
        for name in ('src/__pycache__/cache.pyc','src/.aws/credentials','src/.DS_Store','src/.cache/result.json'):
            with self.subTest(name=name):
                self.add(name,'local configuration',force=True)
                self.assertIn('NON_PROJECT_PATH',self.codes())
                self.git('rm','--cached',name)

    def test_private_filenames_and_case_variants_are_blocked(self):
        for name in ('src/Factory/internal.txt','docs/AGENT_WORKFLOW.MD','data/FACTORY_RUN_DIR.csv','src/private\nnotes.py'):
            with self.subTest(name=name):
                self.add(name,'local procedures',force=True)
                self.assertTrue(self.codes())
                self.git('rm','--cached',name)

    def test_nested_private_paths_are_ignored_locally(self):
        for name in ('source/.factory/state.json','source/factory/engine.py','docs/project/review.json','src/.aws/credentials'):
            with self.subTest(name=name):self.git('check-ignore',name)

    def test_binary_review_is_bound_to_exact_artifact_bytes(self):
        raw=b'\x89PNG\x00\xffproject figure'
        self.add('figures/result.png',raw)
        self.assertIn('UNREVIEWED_BINARY',self.codes())
        policy=p.load_policy(self.root)
        policy['approved_binary_artifacts']['figures/result.png']={
            'sha256':hashlib.sha256(raw).hexdigest(),'reason':'Inspected rendered figure and metadata for project publication.'}
        write_json(self.root/p.POLICY,policy)
        self.assertEqual(p.check(self.root)['status'],'PASS')
        self.add('figures/result.png',raw+b'changed')
        self.assertIn('UNREVIEWED_BINARY',self.codes())

    def test_secrets_and_local_paths_report_locations_only(self):
        secret='ghp_'+'A'*36
        self.add('source/main.py',secret+'\n/Users/developer/private/data\n')
        report=p.check(self.root)
        self.assertTrue({'ACCESS_TOKEN','LOCAL_HOST_PATH'}<={x['code'] for x in report['errors']})
        self.assertNotIn(secret,json.dumps(report))
        self.assertNotIn('/Users/developer',json.dumps(report))

    def test_links_are_not_blindly_published(self):
        path=self.root/'source/link';path.parent.mkdir()
        path.symlink_to('../project/research_plan.json');self.git('add','source/link')
        self.assertIn('UNINSPECTED_LINK',self.codes())

    def test_existing_hooks_are_chained_and_failure_preserved(self):
        old=self.root/'old-hooks';old.mkdir()
        prior=old/'pre-commit';prior.write_text('#!/bin/sh\necho prior > project/prior.txt\nexit 19\n');prior.chmod(0o700)
        self.git('config','core.hooksPath',str(old));p.initialize(self.root)
        result=self.git('commit','-m','Add evaluator',ok=False)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual((self.root/'project/prior.txt').read_text().strip(),'prior')
        self.assertEqual(p.load_policy(self.root)['previous_hooks']['pre-commit'],str(prior))
        p.initialize(self.root)
        self.assertEqual(p.load_policy(self.root)['previous_hooks']['pre-commit'],str(prior))

    def test_prior_push_hook_gets_original_ref_stream(self):
        old=self.root/'old-hooks';old.mkdir()
        prior=old/'pre-push';prior.write_text('#!/bin/sh\ncat > project/push-input.txt\n');prior.chmod(0o700)
        self.git('config','core.hooksPath',str(old));p.initialize(self.root)
        self.commit();self.remote();self.git('push','origin','main')
        self.assertIn('refs/heads/main',(self.root/'project/push-input.txt').read_text())

    def test_bad_push_is_blocked_before_prior_upload_hook(self):
        old=self.root/'old-hooks';old.mkdir()
        prior=old/'pre-push';prior.write_text('#!/bin/sh\necho uploaded > project/uploaded.txt\n');prior.chmod(0o700)
        self.git('config','core.hooksPath',str(old));p.initialize(self.root)
        self.add('source/main.py','# gatekeeper.py\n');self.commit(bypass=True)
        self.remote();self.assertNotEqual(self.git('push','origin','main',ok=False).returncode,0)
        self.assertFalse((self.root/'project/uploaded.txt').exists())

    def test_existing_ignore_patterns_preserved_without_naming_framework(self):
        (self.root/'.gitignore').write_text('/factory/\n/project/\nsource/generated/\n# model factory cache\n')
        p.initialize(self.root)
        text=(self.root/'.gitignore').read_text()
        self.assertNotIn('/factory/',text);self.assertNotIn('/project/',text)
        self.assertIn('# model factory cache',text)
        self.git('check-ignore','source/generated/output.csv')
        self.git('add','.gitignore')
        self.assertEqual(p.check(self.root)['status'],'PASS')

    def test_disabled_hooks_or_ignore_gap_blocks(self):
        self.git('config','core.hooksPath','missing-hooks')
        self.assertIn('HOOKS_NOT_INSTALLED',self.codes())
        p.initialize(self.root)
        (self.root/'.gitignore').write_text('!factory/\n!factory/**\n')
        # info/exclude cannot override a tracked ignore file's explicit unignore.
        self.assertIn('IGNORE_GAP',self.codes())

    def test_policy_is_private_and_malformed_policy_fails_closed(self):
        policy=p.load_policy(self.root)
        for value in (None,32,False):
            with self.subTest(value=value):
                policy['approved_binary_artifacts']={'figures/result.png':{'sha256':value,'reason':'Specific review of the rendered figure.'}}
                write_json(self.root/p.POLICY,policy)
                with self.assertRaises(EvidenceError):p.check(self.root)

    def test_nested_workspace_refused(self):
        nested=self.root/'nested';nested.mkdir()
        with self.assertRaises(EvidenceError):p.initialize(nested)

    def test_linked_worktree_cannot_change_shared_hooks_silently(self):
        self.commit();linked=Path(self.temp.name)/'linked'
        self.git('worktree','add','-b','feature',str(linked))
        shared=self.git('config','--local','--get','core.hooksPath').stdout
        with self.assertRaisesRegex(EvidenceError,'worktreeConfig'):p.initialize(linked)
        self.assertEqual(self.git('config','--local','--get','core.hooksPath').stdout,shared)
        self.assertFalse((linked/p.POLICY).exists())

    def test_configured_worktree_installs_independent_local_hooks(self):
        self.commit();linked=Path(self.temp.name)/'linked'
        self.git('config','extensions.worktreeConfig','true')
        self.git('worktree','add','-b','feature',str(linked))
        self.git('config','--worktree','core.hooksPath','primary-hooks')
        p.initialize(linked)
        self.assertEqual(p.check(linked)['status'],'PASS')
        self.assertEqual(self.git('config','--get','core.hooksPath').stdout.strip(),b'primary-hooks')

    def test_cli_returns_publication_exit_code(self):
        self.add('source/main.py','# gatekeeper.py\n')
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(g.main(['verify-publication',str(self.root),'--staged-only']),44)
        self.assertEqual(json.loads(output.getvalue())['status'],'BLOCKED')

    def test_audit_includes_and_enforces_publication(self):
        from tests.test_v3 import fixture
        study=Path(self.temp.name)/'study';study.mkdir();fixture(study)
        p.initialize(study)
        with contextlib.redirect_stdout(io.StringIO()):
            g.freeze(study);self.assertEqual(g.run_exp(study,'known'),0)
            clean=g.audit_snapshot(study,g.plan_at(study))
        self.assertFalse(clean['errors'])
        self.assertIn('PUBLICATION',clean['checks_executed'])
        leak=study/'factory/local.txt';leak.parent.mkdir();leak.write_text('private procedures')
        p._git(study,'add','-f','factory/local.txt')
        with contextlib.redirect_stdout(io.StringIO()):
            blocked=g.audit_snapshot(study,g.plan_at(study))
            self.assertEqual(g.certify(study),g.EXIT_SCIENCE)
        self.assertIn('PUBLICATION',{entry['code'] for entry in blocked['errors']})

    def test_init_installs_publication_by_default(self):
        fresh=Path(self.temp.name)/'new-project';fresh.mkdir()
        with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(g.main(['init',str(fresh)]),0)
        self.assertEqual(p.check(fresh)['status'],'PASS')
        self.assertTrue((fresh/p.POLICY).is_file())

    def test_project_bootstrap_script_does_not_exempt_publication(self):
        fresh=Path(self.temp.name)/'study-project';(fresh/'factory').mkdir(parents=True)
        (fresh/'factory/VERSION').write_text('3.3.0\n')
        (fresh/'bootstrap.sh').write_text('#!/bin/sh\necho prepare study\n')
        (fresh/'README.md').write_text('# Study analyzer\n')
        self.assertEqual(p.initialize(fresh)['status'],'INSTALLED')
        self.assertTrue((fresh/p.POLICY).is_file())

    def test_release_check_blocks_unmanaged_existing_git(self):
        (self.root/p.POLICY).unlink()
        self.assertEqual(p.release_check(self.root)['status'],'BLOCKED')

    def test_release_check_no_git_is_explicit(self):
        other=Path(self.temp.name)/'no-git';other.mkdir()
        self.assertEqual(p.release_check(other)['status'],'NOT_INITIALIZED')

    def test_version_unchanged_and_distribution_setup_does_not_modify_git(self):
        factory=Path(g.__file__).resolve().parent
        self.assertEqual(g.VERSION,'3.3.0');self.assertEqual((factory/'VERSION').read_text().strip(),'3.3.0')
        if p.is_distribution(factory.parent):
            self.assertEqual(p.initialize(factory.parent)['status'],'DISTRIBUTION')
        else:
            with tempfile.TemporaryDirectory() as dist_temp:
                droot=Path(dist_temp);(droot/'bootstrap.sh').touch();(droot/'factory').mkdir()
                (droot/'factory/VERSION').write_text('3.3.0\n')
                (droot/'README.md').write_text('# Software Factory 3.3.0\n')
                self.assertEqual(p.initialize(droot)['status'],'DISTRIBUTION')

if __name__=='__main__':unittest.main()
