import os
import re
import sys
import pdb
import json
import yaxil
import pydicom
import logging
import requests
from io import BytesIO
from pprint import pprint
from yaxil.exceptions import NoExperimentsError

logger = logging.getLogger()

class Tagger:
    def __init__(self, alias, config, target, session, append_tag_digits, project=None, cache=None):
        self.auth = yaxil.auth(alias)
        self.config = config
        self.project = project
        self.cache = cache
        self.target = target 
        self.session = session
        self.append_tag_digits = append_tag_digits
        self.updates = dict()

    def generate_updates(self):
        self.get_scan_listing()
        if 'dwi' in self.target:
            self.updates.update({
                'dwi': self.dwi(self.scans), # Generate updates for main DWI scan(s)
                'dwi_PA': self.dwi_PA(self.scans), # Generate updates for PA fieldmap(s)
                'dwi_AP': self.dwi_AP(self.scans), # Generate updates for AP fieldmap(s)
                'revpol': self.revpol(self.scans) # Generate updates for revpol scans
            })
        if 't1w' in self.target:
            self.updates.update({
                't1w': self.t1w(self.scans),  # Generate updates for T1w scan(s)
                't1w_move': self.t1w_move(self.scans)  # Generate updates for T1w_MOVE scan(s)
            })
        if 't2w' in self.target:
            self.updates.update({
                't2w': self.t2w(self.scans),  # Generate updates for T2w scan(s)
                't2w_move': self.t2w_move(self.scans)  # Generate updates for T2w_MOVE scan(s)
            })
        if 'bold' in self.target:
            self.updates.update({
                'bold': self.bold(self.scans),
                'bold_PA': self.bold_PA(self.scans),
                'bold_AP': self.bold_AP(self.scans)
                })
        if 'all' in self.target:
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

        # filter out None values

        filtered = {key: value for key, value in self.updates.items() if value is not None}
        self.updates.clear()
        self.updates.update(filtered)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        yaxil.end_session(self.auth)
        return False

    def apply_updates(self):
        self.upsert()

    def filter(self, modality):
        matches = []
        tags = []
        try:
            filt = self.config[modality]
        except KeyError:
            logger.warning(f'{modality} not found in config file. continuing.')
            return None, None
        for scan in self.scans:
            scanid = scan['id']
            for f in filt:
                tag = f['tag']
                logger.debug(f'trying to find match for {tag}')
                match = True
                for key, expected in iter(f.items()):
                    if key == 'tag':
                        continue
                    actual = scan.get(key, None)
                    if actual != expected:
                        match = False
                    else:
                        logger.debug(f'MATCH {actual} == {expected} for {scanid}')
                if match:
                    matches.append(scan)
                    tags.append(tag)
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
            tag_prefix = tags[tag_counter]
            match = re.search(r'\d+$', tag_prefix) ### check if the tag ends in digits. If it does don't mess with it
            if not match:
                if not self.append_tag_digits and len(scans) < 2:
                    tag = tag_prefix
                else:
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
        scans, tags = self.filter('t1w_move')
        if not scans:
            return None
        tag_counter = 0  
        for i,scan in enumerate(scans, start=1):
            sid = scan['id']
            session = scan['session_label']
            series = scan['series_description'].strip()
            note = scan['note'].strip()
            #tag = f'#T1w_MOVE_{i:03}'
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


    def t2w(self, scans):
        updates = list()
        scans, tags = self.filter('t2w')
        if not scans:
            return None
        tag_counter = 0
        for i,scan in enumerate(scans, start=1):
            sid = scan['id']
            session = scan['session_label']
            series = scan['series_description'].strip()
            note = scan['note'].strip()
            #tag = f'#T2w_{i:03}'
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


    def t2w_move(self, scans):
        updates = list()
        scans, tags = self.filter('t2w_move')
        if not scans:
            return None
        tag_counter = 0
        for i,scan in enumerate(scans, start=1):
            sid = scan['id']
            session = scan['session_label']
            series = scan['series_description'].strip()
            note = scan['note'].strip()
            #tag = f'#T2w_MOVE_{i:03}'
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
        tag_counter = 0
        for i, scan in enumerate(scans, start=1):
            sid = scan['id']
            session = scan['session_label']
            series = scan['series_description'].strip()
            note = scan['note'].strip()
            tag_prefix = tag[tag_counter]
            match = re.search(r'\d+$', tag_prefix)
            #tag = f'#DWI_FMAP_PA_{i:03}'
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


    def dwi_AP(self, scans):
        updates = list()
        scans, tag = self.filter('dwi_AP')
        if not scans:
            return None
        tag_counter = 0
        for i, scan in enumerate(scans, start=1):
            sid = scan['id']
            session = scan['session_label']
            series = scan['series_description'].strip()
            note = scan['note'].strip()
            tag_prefix = tag[tag_counter]
            match = re.search(r'\d+$', tag_prefix)
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
                return None
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
            logger.debug(f'{cachefile}')
            self.scans = self.query_scans()
            if self.cache:
                logger.info(f'saving {cachefile}')
                with open(cachefile, 'w') as fo:
                    fo.write(json.dumps(self.scans, indent=2))
        else:
            logger.info(f'cache hit {cachefile}')
            with open(cachefile) as fo:
                self.scans = json.loads(fo.read())

    def query_scans(self):
        result = list()
        scans = list(yaxil.scans(self.auth, label=self.session))
        logger.info('querying scans...')
        for scan in scans:
            # turn image type back into a proper list
            image_type = scan.get('image_type', None)
            if isinstance(image_type, str) and image_type:
                scan['image_type'] = re.split(r'\\+', image_type)
            # pull out secondary image type from an actual dicom file
            sec_image_type = self.secondary_image_type(scan)
            scan['secondary_image_type'] = sec_image_type
        return scans

    def secondary_image_type(self, scan):
        # request a single dicom file from this scan
        ds = self.get_example_file(scan)

        # only enhanced dicom files have this attribute
        if not hasattr(ds, 'PerFrameFunctionalGroupsSequence'):
            return list()

        # search for secondary image type
        try:
            item = ds.PerFrameFunctionalGroupsSequence[0]
            item = item[(0x0021,0x11fe)][0]
            item = item[(0x0021,0x1175)]
            return list(item.value)
        except KeyError:
            pass
        
        try:
            item = ds.PerFrameFunctionalGroupsSequence[0]
            item = item[(0x0021,0x10fe)][0]
            item = item[(0x0021,0x1075)]
            return list(item.value)
        except KeyError:
            pass

        return list()

    def get_example_file(self, scan):
        baseurl = self.auth.url.rstrip('/')
        project = scan['session_project']
        subject = scan['subject_label']
        session = scan['session_label']
        scanid = scan['id']
        url = f'{baseurl}/data/projects/{project}/subjects/{subject}/experiments/{session}/scans/{scanid}/files'
        r = requests.get(
            url,
            auth=yaxil.basicauth(self.auth),
            cookies=self.auth.cookie
        )
        if r.status_code != requests.codes.ok:
            raise RequestError(f'response not ok ({r.status_code}) from {r.url}')
        js = r.json()
        path = js['ResultSet']['Result'][0]['URI'].lstrip('/')
        r = requests.get(
            f'{baseurl}/{path}',
            auth=yaxil.basicauth(self.auth),
            cookies=self.auth.cookie
        )
        if r.status_code != requests.codes.ok:
            raise RequestError(f'response not ok ({r.status_code}) from {r.url}')
        ds = pydicom.dcmread(BytesIO(r.content))
        return ds

class RequestError(Exception):
    pass

class BadArgumentError(Exception):
    pass

class UpsertError(Exception):
    pass
