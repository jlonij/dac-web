#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# DAC Entity Linker
#
# Copyright (C) 2017-2018 Koninklijke Bibliotheek, National Library of
# the Netherlands
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# Standard library imports
import codecs
import json
import os
import re
import sys

# External library imports
import requests
import xml.etree.ElementTree as etree

from bottle import abort
from bottle import default_app
from bottle import get
from bottle import post
from bottle import template
from bottle import redirect
from bottle import request
from bottle import response
from bottle import route
from bottle import run
from bottle import static_file

# Add absolute path to the Bottle template path
import bottle
abs_path = os.path.dirname(os.path.realpath(__file__))
bottle.TEMPLATE_PATH.insert(0, os.path.join(abs_path, 'templates'))
bottle.TEMPLATE_PATH.insert(0, abs_path)

# DAC imports
sys.path.insert(0, os.path.join(*[abs_path, '..', 'dac', 'dac']))
import dac
import models

@get('/<name>')
def show_candidates(name):
    '''
    Present an entity and its candidate links for annotation.
    '''
    # Load json data from file
    path = os.path.join(*[abs_path, 'users', name, 'art.json'])
    data = json.load(codecs.open(path, 'r', 'utf-8'))

    # Get instance index or id
    no_instances = len(data['instances'])
    last_instance = no_instances - 1

    if request.query.id:
        index = None
        for i in data['instances']:
            if i['id'] == int(request.query.id):
                index = data['instances'].index(i)
                break
        if not index:
            abort(500, 'Identifier not found in dataset.')
    elif request.query.index:
        index = int(request.query.index)
    else:
        # First instance that hasn't been linked yet
        index = 0
        for i in data['instances']:
            if not i['links']:
                index = data['instances'].index(i)
                break
    if index >= no_instances:
        index = 0
    if index <= -1:
        index = last_instance

    # Get instance data
    instance_id = data['instances'][index]['id']
    url = data['instances'][index]['url']
    ne = data['instances'][index]['ne_string']
    ne_type = data['instances'][index]['ne_type']
    links = data['instances'][index]['links']

    # Get OCR and publication year
    context = dac.Context(url)
    ocr = re.sub('(?P<pf>(^|\W|:punct:))' + re.escape(ne) +
                 '(?P<sf>(\W|$|:punct:))', '\g<pf>' +
                 '<span style="background-color:yellow;">' +
                 ne + '</span>' + '\g<sf>', context.ocr)

    # Get candidates
    cluster = dac.Cluster([dac.Entity(ne, tpta_type=ne_type, context=context)])

    if cluster.entities[0].valid:
        model = models.BaseModel()
        cand_list = dac.CandidateList(cluster, model)
        candidates = cand_list.candidates
    else:
        candidates = []

    return template('index', last_instance=last_instance, index=index,
                    instance_id=instance_id, url=url, ne=ne, ne_type=ne_type,
                    publ_date=context.publ_year, ocr=ocr, links=links,
                    candidates=candidates)


@get('/predict')
def predict():
    '''
    Get the current DAC prediction.
    '''
    linker = dac.EntityLinker(debug=True, candidates=True)
    result = linker.link(request.query.url, request.query.ne.encode('utf-8'))
    result = result['linkedNEs'][0]
    response.set_header('Content-Type', 'application/json')
    return result


@post('/<name>')
def save_links(name):
    '''
    Save selected links for an entity.
    '''
    index = int(request.forms.get('index'))
    links = request.forms.getall('links')

    if 'other' in links:
        links = [l for l in links if l != 'other']
        links.append(request.forms.get('other_link'))
    action = request.forms.get('action')

    orig_file = os.path.join(*[abs_path, 'users', name, 'art.json'])
    temp_file = os.path.join(*[abs_path, 'users', name, 'temp.json'])

    # Load json data from file
    data = json.load(open(orig_file))

    # Set new link value
    data['instances'][index]['links'] = [l.decode('utf-8') for l in links]

    # Save json data to temp file
    with codecs.open(temp_file, 'w', 'utf-8') as fh:
        json.dump(data, fh, indent=4, sort_keys=True, ensure_ascii=False)

    # Check temp file existence and size
    if os.path.exists(temp_file) and (abs(os.path.getsize(orig_file) -
                                          os.path.getsize(temp_file)) < 15000):
        os.chmod(temp_file, 0777)
        os.remove(orig_file)
        os.rename(temp_file, orig_file)

        # Redirect to next page
        redirect_url = '../{}'.format(name)

        if action == 'first':
            redirect_url += '?index=0'

        elif action == 'next_art':
            next_index = 0
            current_url = data['instances'][index]['url']
            for i in data['instances'][index:]:
                if i['url'] != current_url:
                    next_index = data['instances'].index(i)
                    break
            redirect_url += '?index={}'.format(next_index)

        elif action == 'prev_art':
            next_index = -1
            current_url = data['instances'][index]['url']
            prev_url = None
            for i in reversed(data['instances'][:index]):
                if i['url'] != current_url:
                    prev_url = i['url']
                    prev_index = data['instances'].index(i)
                    next_index = 0
                    for j in reversed(data['instances'][:prev_index]):
                        if j['url'] != prev_url:
                            next_index = data['instances'].index(j) + 1
                            break
                    break
            if next_index == -1:
                prev_url = data['instances'][-1]['url']
                for i in data['instances'][::-1]:
                    if i['url'] != prev_url:
                        next_index = data['instances'].index(i) + 1
                        break

            redirect_url += '?index={}'.format(next_index)

        elif action == 'next':
            redirect_url += '?index={}'.format(index + 1)

        elif action == 'prev':
            redirect_url += '?index={}'.format(index - 1)

        redirect(redirect_url)

    else:
        abort(500, 'Error saving data.')


@get('/<name>/edit')
def update_training_set(name):
    '''
    Add or delete an entity or an article.
    '''
    action = request.query.action
    url = request.query.url
    ne = request.query.ne
    link = request.query.link
    callback = request.query.callback

    response.set_header('Content-Type', 'application/json')
    result = {}

    if not action or action not in ['add', 'delete'] or not url:
        result['status'] = 'error'
        result['message'] = 'Invoke with ?action=[add|delete]&url=[url]'
        if callback:
            result = unicode(callback) + u'(' + json.dumps(result) + u');'
        return result

    orig_file = os.path.join(*[abs_path, 'users', name, 'art.json'])
    temp_file = os.path.join(*[abs_path, 'users', name, 'temp.json'])

    # Load json data from file
    data = json.load(codecs.open(orig_file, 'r', 'utf-8'))

    # Add article or NE
    if action == 'add':
        # Check if article and / or NE isn't included already in current set
        for i in data['instances']:
            if i['url'] == url:
                print('found url in this set')
                if not ne or i['ne_string'] == ne:
                    result['status'] = 'error'
                    result['message'] = 'Article or entity already in data set'
                    if callback:
                        result = (unicode(callback) + u'(' +
                                  json.dumps(result) + u');')
                    return result

        # Check if article isn't included in another set
        to_check = (['tve'] if name.startswith('test') else
                    ['test', 'test-clean', 'test-spotlight'])
        for f in to_check:
            alt_file = os.path.join(*[abs_path, 'users', f, 'art.json'])
            with codecs.open(alt_file, 'r', 'utf-8') as fh:
                alt_data = json.load(fh)
                for i in alt_data['instances']:
                    if i['url'] == url:
                        print('found url in other set')
                        result['status'] = 'error'
                        result['message'] = 'Article already in other data set'
                        if callback:
                            result = (unicode(callback) + u'(' +
                                      json.dumps(result) + u');')
                        return result

        next_id = data['instances'][-1]['id'] + 1

        if ne:
            # Add single NE
            i = {}
            i['url'] = url
            i['ne_string'] = ne
            i['ne_type'] = None
            i['links'] = [link] if link else []
            i['id'] = next_id
            data['instances'].append(i)
        else:
            # Add article
            resp = requests.get(dac.TPTA_URL, params={'url': url})
            resp.encoding = 'utf-8'
            ner_data = resp.json()

            entities = []
            next_id = data['instances'][-1]['id'] + 1

            if ner_data['entities']:
                for e in ner_data['entities']:
                    if e['ne'] not in entities:
                        entities.append(e['ne'])
                        i = {}
                        i['url'] = url
                        i['ne_string'] = e['ne']
                        i['ne_type'] = e['type']
                        i['links'] = []
                        i['id'] = next_id
                        next_id += 1
                        data['instances'].append(i)
            else:
                result['status'] = 'error'
                result['message'] = 'No entities found for article'
                if callback:
                    result = (unicode(callback) + u'(' +
                              json.dumps(result) + u');')
                return result

    # Delete article or NE
    if action == 'delete':
        # Check if article can be found
        to_remove = []
        for i in data['instances']:
            if i['url'] == url:
                if not ne or i['ne_string'] == ne:
                    to_remove.append(i)

        if not to_remove:
            result['status'] = 'error'
            result['message'] = 'Article or entity not found in dataset'
            if callback:
                result = unicode(callback) + u'(' + json.dumps(result) + u');'
            return result
        else:
            for i in to_remove:
                data['instances'].remove(i)

    # Save json data to temp file
    with codecs.open(temp_file, 'w', 'utf-8') as fh:
        json.dump(data, fh, indent=4, sort_keys=True, ensure_ascii=False)

    # Check temp file existence and size
    if os.path.exists(temp_file) and (abs(os.path.getsize(orig_file) -
                                      os.path.getsize(temp_file)) < 50000):
        os.chmod(temp_file, 0777)
        os.remove(orig_file)
        os.rename(temp_file, orig_file)
    else:
        result['status'] = 'error'
        result['message'] = 'Error saving data'
        if callback:
            result = unicode(callback) + u'(' + json.dumps(result) + u');'
        return result

    result['status'] = 'success'
    if callback:
        result = unicode(callback) + u'(' + json.dumps(result) + u');'
    print(result)
    return result


@route('/static/<filename:path>')
def static(filename):
    '''
    Load static css, js files.
    '''
    return static_file(filename, root=abs_path + '/static')


if __name__ == '__main__':
    run(host='localhost', port=5001)
else:
    application = default_app()
