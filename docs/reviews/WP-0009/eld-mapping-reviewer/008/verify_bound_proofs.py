"""Independent CPU proof reconciliation; all external inputs are immutable Git bytes."""
import datetime,json
import finalize_evidence_v2 as f
c=f.c
def when(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def main():
    author=c.GitReader(f.AUTHOR);reviewer=c.GitReader('bddc02ad6e4824850b8865ccdf062b88ca5eaa55');inputs=[];out={}
    inventory=c.load(author.read('docs/research/WP-0009/eld-mapping-author/fresh-comparison/deliverable-verification.json'))
    old=f.trees(inventory['base']);new=f.trees(inventory['deliverable'])
    c.require(all(new.get(k)==v for k,v in old.items()),'Author modified protected content')
    added=set(new)-set(old);c.require(added=={x['path'] for x in inventory['changed_files']} and len(added)==100,'Author inventory incomplete')
    for x in inventory['changed_files']:
        data=author.read(x['path']);c.require(c.sha(data)==x['published_sha256'] and len(data)==x['published_bytes'] and new[x['path']].split()[-1]==x['git_blob'],'Author inventory identity mismatch')
    collection=c.load(author.read('docs/evidence/WP-0009/eld-mapping-author/007/attempt-1/collection.json'))
    for x in collection['copied_files']:
        data=author.read(x['destination']);c.require(c.sha(data)==x['sha256'] and len(data)==x['bytes'],'Author retained copy identity mismatch')
    out['author_inventory']={'added_paths':len(added),'unchanged_base_paths':len(old),'published_copied_files':len(collection['copied_files']),'original_comparison_scope':'Published hashes independently reproduced; root publication audit separately checked external originals.'}
    for owner,reader,rev,prefix,authority,head,return_rev in [
        ('author',author,f.AUTHOR,'docs/evidence/WP-0009/eld-mapping-author/007/attempt-1','6343ded1cd79b7c5b67b34893fe4516dc6845eb9','2a3781745cb120f6e3eb22b234c111241ba8d8c9','70d45a144f44b74e562c1dbe8fdcea16662e970b'),
        ('reviewer',reviewer,reviewer.revision,'docs/evidence/WP-0009/eld-mapping-reviewer/008/publication-attempt-2','e339bd4c8322a14fbff98d9299acede4b92c911f',f.BASE,f.AFTER)]:
        auth=c.GitReader(authority);release=c.load(auth.read('docs/coordination/WP-0009/releases/'+owner+'.json'))
        after=c.GitReader(return_rev);afterprefix='docs/coordination/WP-0009/'+owner+'-after/'
        for path in c.git('ls-tree','-r','--name-only',return_rev,'--',afterprefix).decode().splitlines():after.read(path)
        receipt=c.load(after.read(afterprefix+'lease-return.json'));postmodel=c.load(after.read(afterprefix+'model.json'))
        pre=c.load(reader.read(prefix+'/run/evidence/preflight.json'));result=c.load(reader.read(prefix+'/run/run-result.json'))
        if owner=='author':
            actual=c.load(reader.read(prefix+'/launch/exit.json'));start=actual['started_utc'];end=actual['finished_utc'];code=actual['exit']
        else:
            launch=c.load(reader.read(prefix+'/launch/launch.json'));actual=c.load(reader.read(prefix+'/launch/supervisor-tool-outcome.json'));start=launch['started_utc'];end=actual['completed_utc'];code=actual['supervisor_exit_code']
        c.require(code==0 and actual['executing_head']==release['executing_head']==head,'Actual supervisor/tool receipt mismatch')
        c.require(when(release['issued_utc'])<=when(start)<when(end)<when(release['expires_utc']),'Execution outside exact lease')
        c.require(receipt['status']=='RETURNED_ACKNOWLEDGED' and receipt['runtime_authority']==authority and receipt['lease']==release['lease']['id'],'Lease return identity mismatch')
        c.require(receipt['bound_model_processes_absent'] is True and receipt['post_observer_codes']==[0,0] and receipt['model_18_objects_and_notice_reverified'] is True and receipt['remaining_task_gpu_leases']==[],'Lease cleanup incomplete')
        c.require(when(receipt['utc'])>when(end),'Lease return precedes supervisor exit')
        for group in ('model','notice'):
            key='files' if group=='model' else 'notices'
            before={x['path']:x for x in pre[group][key]};afterobjects={x['path']:x for x in postmodel[group][key]}
            c.require(before.keys()==afterobjects.keys(),'Post-run identity set mismatch')
            for name,x in before.items():c.require(x['sha256']==afterobjects[name]['sha256'] and x['size']==afterobjects[name]['size'] and afterobjects[name]['ok'] is True,'Post-run identity changed')
        c.require(result['free_bytes_after']>=20*(1<<30) and result['owned_bytes_after']<=4*(1<<30) and result['elapsed_s']<6*3600,'Finite resource bound exceeded')
        out[owner]={'supervisor_tool_receipt':actual,'started_utc':start,'finished_utc':end,'issued_utc':release['issued_utc'],'expires_utc':release['expires_utc'],'lease_return':receipt,'model_notice_before_after_exact':True,'storage_time_bounds_pass':True,'process_evidence':c.load(after.read(afterprefix+'processes-and-outcome.json'))}
        inputs.extend(auth.inputs.values());inputs.extend(after.inputs.values())
    c.require(when(out['author']['lease_return']['utc'])<when(out['reviewer']['issued_utc']),'Model-job leases overlapped')
    inputs.extend(author.inputs.values());inputs.extend(reviewer.inputs.values());out['input_inventory']=inputs
    f.write(f.HERE/'bound-proof-verification.json',{'status':'PASS','helper_commit':c.git('rev-parse','HEAD').decode().strip(),'checks':out})
    print(json.dumps({'status':'PASS','author_entries':len(added),'author_copies':len(collection['copied_files']),'protected_author_paths':len(old),'immutable_input_files':len(inputs)}))
if __name__=='__main__':main()
