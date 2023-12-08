import os
import re
import sys
import json
import yaxil
import logging
import requests
from yaxil.exceptions import NoExperimentsError

logger = logging.getLogger()

class Tagger:
    def __init__(self, alias, config, target, session, project=None, cache=None):
        self.auth = yaxil.auth(alias)
        self.config = config
        self.project = project
        self.cache = cache
        self.target = target 
        self.session = session
        self.updates = dict()

    def generate_updates(self):
        self.get_scan_listing()
        if self.target == 'dwi':
            self.updates.update({
                'dwi': self.dwi(self.scans), # Generate updates for main DWI scan(s)
                'dwi_PA': self.dwi_PA(self.scans), # Generate updates for PA fieldmap(s)
                'dwi_AP': self.dwi_AP(self.scans), # Generate updates for AP fieldmap(s)
                'revpol': self.revpol(self.scans) # Generate updates for revpol scans
            })
        elif self.target == 't1':
            self.updates.update({
                't1w': self.t1w(self.scans),  # Generate updates for T1w scan(s)
                't1w_move': self.t1w_move(self.scans)  # Generate updates for T1w_MOVE scan(s)
            })
        elif self.target == 't2':
            self.updates.update({
                't2w': self.t2w(self.scans),  # Generate updates for T2w scan(s)
                't2w_move': self.t2w_move(self.scans)  # Generate updates for T2w_MOVE scan(s)
            })
        elif self.target == 'bold':
            self.updates.update({
                'bold': self.bold(self.scans),
                'bold_PA': self.bold_PA(self.scans),
                'bold_AP': self.bold_AP(self.scans)
                })
        elif self.target == 'all':
            self.updates.update({
                't1w': self.t1w(self.scans),  # Generate updates for T1w scan(s)
                't1w_move': self.t1w_move(self.scans),  # Generate updates for T1w_MOVE scan(s)
                't2w': self.t2w(self.scans),  # Generate updates for T2w scan(s)
                't2w_move': self.t2w_move(self.scans),  # Generate updates for T2w_MOVE scan(s)
                'dwi': self.dwi(self.scans), # Generate updates for main DWI scan(s)
                'dwi_PA': self.dwi_PA(self.scans), # Generate updates for PA fieldmap(s)
                'dwi_AP': self.dwi_AP(self.scans), # Generate updates for AP fieldmap(s)
                'bold': self.bold(self.scans), # Generate updates for bold scans
                'bold_PA': self.bold_PA(self.scans), # Generate updates for bold pa fieldmap(s)
                'bold_AP': self.bold_AP(self.scans), # Generate updates for bolda p fieldmap(s)
                'revpol': self.revpol(self.scans) # Generate updates for revpol scans
            })

    def apply_updates(self):
        self.upsert()

    def filter(self, modality):
        matches = []
        tags = []
        try:
            filt = self.config[modality]
        except KeyError:
            logger.warning(f'{modality} not found in config file. continuing.')
            return None
        for scan in self.scans:
            image_type = scan.get('image_type', None)
            if isinstance(image_type, str):
                scan['image_type'] = re.split('\\\+', scan['image_type'])
            for f in filt:
                match = True
                for key, value in iter(f.items()):
                    if key in scan and scan[key] != value:
                        match = False
                if match:
                    matches.append(scan)
                    tags.append(f['tag'])
        return matches, tags

    def t1w(self, scans):
        updates = list()
        scans, tags = self.filter('t1w')
        if not scans:
            return None
        tag_counter = 0
        for i, scan in enumerate(scans, start=1):
            sid = scan['id']
            session = scan['session_label']
            series = scan['series_description'].strip()
            note = scan['note'].strip()
            #tag = f'{tag}_{i:03}'
            tag_prefix = tags[tag_counter]
            match = re.search(r'\d+$', tag_prefix) ### check if the tag ends in digits. If it does don't mess with it
            if not match:
                tag = tag_prefix + f'_{i:03}'
            else:
                tag = tag_prefix
            tag_counter += 1
            updates.append({
                'project': scan['session_project'],
                'subject': scan['subject_label'],
                'session': session, 
                'scan': sid,
                'series_description': series,
                'note': note,
                'tag': tag
            })
        return updates

    def t1w_move(self, scans):
        updates = list()
        scans, tag = self.filter('t1w_move')
        if not scans:
            return None        
        for i,scan in enumerate(scans, start=1):
            sid = scan['id']
            session = scan['session_label']
            series = scan['series_description'].strip()
            note = scan['note'].strip()
            #tag = f'#T1w_MOVE_{i:03}'
            tag = f'{tag}_{i:03}'
            updates.append({
                'project': scan['session_project'],
                'subject': scan['subject_label'],
                'session': session, 
                'scan': sid,
                'series_description': series,
                'note': note,
                'tag': tag
            })
        return updates


    def t2w(self, scans):
        updates = list()
        scans, tag = self.filter('t2w')
        if not scans:
            return None    
        for i,scan in enumerate(scans, start=1):
            sid = scan['id']
            session = scan['session_label']
            series = scan['series_description'].strip()
            note = scan['note'].strip()
            #tag = f'#T2w_{i:03}'
            tag = f'{tag}_{i:03}'
            updates.append({
                'project': scan['session_project'],
                'subject': scan['subject_label'],
                'session': session, 
                'scan': sid,
                'series_description': series,
                'note': note,
                'tag': tag
            })
        return updates


    def t2w_move(self, scans):
        updates = list()
        scans, tag = self.filter('t2w_move')
        if not scans:
            return None
        for i,scan in enumerate(scans, start=1):
            sid = scan['id']
            session = scan['session_label']
            series = scan['series_description'].strip()
            note = scan['note'].strip()
            #tag = f'#T2w_MOVE_{i:03}'
            tag = f'{tag}_{i:03}'
            updates.append({
                'project': scan['session_project'],
                'subject': scan['subject_label'],
                'session': session, 
                'scan': sid,
                'series_description': series,
                'note': note,
                'tag': tag
            })
        return updates


    def dwi(self, scans):
        updates = list()
        scans, tags = self.filter('dwi')
        if not scans:
            return None
        tag_counter = 0
        for i, scan in enumerate(scans, start=1):
            sid = scan['id']
            session = scan['session_label']
            series = scan['series_description'].strip()
            note = scan['note'].strip()
            #tag = f'#DWI_MAIN_{i:03}'
            tag_prefix = tags[tag_counter]
            match = re.search(r'\d+$', tag_prefix) ### check if the tag ends in digits. If it does don't mess with it
            if not match:
                tag = tag_prefix + f'_{i:03}'
            else:
                tag = tag_prefix
            tag_counter += 1
            updates.append({
                'project': scan['session_project'],
                'subject': scan['subject_label'],
                'session': session, 
                'scan': sid,
                'series_description': series,
                'note': note,
                'tag': tag
                })
        return updates

    def revpol(self, scans):
        updates = list()
        scans, tags = self.filter('revpol')
        if not scans:
            return None
        tag_counter = 0
        for i, scan in enumerate(scans, start=1):
            sid = scan['id']
            session = scan['session_label']
            series = scan['series_description'].strip()
            note = scan['note'].strip()
            tag_prefix = tags[tag_counter]
            match = re.search(r'\d+$', tag_prefix) ### check if the tag ends in digits. If it does then don't mess with it
            if not match:
                tag = tag_prefix + f'_{i:03}'
            else:
                tag = tag_prefix
            tag_counter += 1
            updates.append({
                'project': scan['session_project'],
                'subject': scan['subject_label'],
                'session': session, 
                'scan': sid,
                'series_description': series,
                'note': note,
                'tag': tag
                })
        return updates

    def dwi_PA(self, scans):
        updates = list()
        scans, tag = self.filter('dwi_PA')
        if not scans:
            return None
        for i, scan in enumerate(scans, start=1):
            sid = scan['id']
            session = scan['session_label']
            series = scan['series_description'].strip()
            note = scan['note'].strip()
            #tag = f'#DWI_FMAP_PA_{i:03}'
            tag = f'{tag}_{i:03}'
            updates.append({
                'project': scan['session_project'],
                'subject': scan['subject_label'],
                'session': session, 
                'scan': sid,
                'series_description': series,
                'note': note,
                'tag': tag
                })
        return updates


    def dwi_AP(self, scans):
        updates = list()
        scans, tag = self.filter('dwi_AP')
        if not scans:
            return None
        for i, scan in enumerate(scans, start=1):
            sid = scan['id']
            session = scan['session_label']
            series = scan['series_description'].strip()
            note = scan['note'].strip()
            #tag = f'#DWI_FMAP_AP_{i:03}'
            tag = f'{tag}_{i:03}'
            updates.append({
                'project': scan['session_project'],
                'subject': scan['subject_label'],
                'session': session, 
                'scan': sid,
                'series_description': series,
                'note': note,
                'tag': tag
                })
        return updates

    def bold(self, scans):
        updates = list()
        scans, tag = self.filter('bold')
        if not scans:
            return None
        for i, scan in enumerate(scans, start=1):
            sid = scan['id']
            session = scan['session_label']
            series = scan['series_description'].strip()
            note = scan['note'].strip()
            #tag = f'#BOLD_{i:03}'
            tag = f'{tag}_{i:03}'
            updates.append({
                'project': scan['session_project'],
                'subject': scan['subject_label'],
                'session': session, 
                'scan': sid,
                'series_description': series,
                'note': note,
                'tag': tag
                })
        return updates

    def bold_PA(self, scans):
        updates = list()
        scans, tag = self.filter('bold_PA')
        if not scans:
            return None
        for i, scan in enumerate(scans, start=1):
            sid = scan['id']
            session = scan['session_label']
            series = scan['series_description'].strip()
            note = scan['note'].strip()
            #tag = f'#BOLD_PA_{i:03}'
            tag = f'{tag}_{i:03}'
            updates.append({
                'project': scan['session_project'],
                'subject': scan['subject_label'],
                'session': session, 
                'scan': sid,
                'series_description': series,
                'note': note,
                'tag': tag
                })
        return updates

    def bold_AP(self, scans):
        updates = list()
        scans, tag = self.filter('bold_AP')
        if not scans:
            return None
        for i, scan in enumerate(scans, start=1):
            sid = scan['id']
            session = scan['session_label']
            series = scan['series_description'].strip()
            note = scan['note'].strip()
            #tag = f'#BOLD_AP_{i:03}'
            tag = f'{tag}_{i:03}'
            updates.append({
                'project': scan['session_project'],
                'subject': scan['subject_label'],
                'session': session, 
                'scan': sid,
                'series_description': series,
                'note': note,
                'tag': tag
                })
        return updates

    def upsert(self, confirm=False):
        updates = list(self._squeeze(self.updates))
        if not updates:
            return
        for scan in self.scans:
            sid = scan['id']
            note = scan['note']
            update = [x for x in updates if x['scan'] == sid]
            if not update:
                continue
            if len(update) > 1:
                raise UpsertError(f'found too many updates for scan {sid}')
            update = update.pop()
            note = update['note'].strip()
            tag = update['tag'].strip()
            if tag not in note:
                upsert = tag
                if note:
                    upsert = f'{tag} {note}'
                logger.info(f'setting note for scan {sid} to "{upsert}"')
                self.setnote(scan, text=upsert, confirm=False)
            else:
                logger.info(f"'{tag}' already in note '{note}'")


    def _squeeze(self, updates):
        for _,items in iter(updates.items()):
            if not items:
                return
            for item in items:
                yield item

    def setnote(self, scan, text=None, confirm=False):
        if not text:
            text = ' '
        project = scan['session_project']
        subject = scan['subject_label'] 
        session = scan['session_label']
        scan_id = scan['id']
        baseurl = self.auth.url.rstrip('/')
        url = f'{baseurl}/data/projects/{project}/subjects/{subject}/experiments/{session}/scans/{scan_id}'
        params = {
            'xnat:mrscandata/note': text
        }
        logger.info(f'setting note for {session} scan {scan_id} to {text}')
        logger.info(f'PUT {url} params {params}')
        if confirm:
            input('press enter to execute request')
        r = requests.put(url, params=params, auth=(self.auth.username, self.auth.password))
        if r.status_code != requests.codes.OK:
            raise SetNoteError(f'response not ok for {url}')

    def get_scan_listing(self):
        '''
        Return scan listing as a list of dictionaries. 
        
        This function attempts to read the scan listing from a 
        cached JSON file. However, if a cached file doesn't exist, 
        one will be created by saving the output from yaxil.scans.
        '''
        cachefile = f'{self.session}.json'
        self.scans = None
        if not os.path.exists(cachefile):
            logger.info(f'cache miss {cachefile}')
            self.scans = list(yaxil.scans(self.auth, label=self.session))
            if self.cache:
                with open(cachefile, 'w') as fo:
                    fo.write(json.dumps(self.scans, indent=2))
        else:
            logger.info(f'cache hit {cachefile}')
            with open(cachefile) as fo:
                self.scans = json.loads(fo.read())

class BadArgumentError(Exception):
    pass

class UpsertError(Exception):
    pass
