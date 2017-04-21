#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# DAC Entity Linker
#
# Copyright (C) 2017 Koninklijke Bibliotheek, National Library of
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

import json
import sys

sys.path.insert(0, "../../dac")

import dac

import unicodecsv as csv

linker = dac.EntityLinker(debug=True)

with open('../users/test/art.json') as fh:
    data = json.load(fh)

keys = ['Id', 'Entity', 'Link', 'Prediction', 'Correct']

with open('results.csv', 'w') as fh:
    csv_writer = csv.writer(fh, delimiter='\t', encoding='utf-8')
    csv_writer.writerow(keys)

    # Get and evaluate results
    nr_instances = 0 # Total number of test examples
    nr_correct_instances = 0 # Number of correctly predicted examples
    nr_links = 0 # Number of examples where correct answer is a link
    nr_correct_links = 0 # Number of link examples that were predicted correctly
    nr_false_links = 0 # Number of examples where incorrect link was predicted

    for i in data['instances']:

        # Check if instance has been properly labeled
        if i['link'] != '':

            print('Evaluating instance ' + str(nr_instances) + ': ' +
                i['ne_string'].encode('utf-8'))

            # Get result for current instance
            result = linker.link(i['url'], i['ne_string'].encode('utf-8'))[0]

            row = []
            row.append(str(nr_instances))
            row.append(i['ne_string'].encode('utf-8'))
            row.append(i['link'].encode('utf-8'))
            row.append(result['link'].encode('utf-8') if 'link' in result
                else result['reason'])

            # Evaluate result
            # A link should be predicted
            if i['link'] != 'none':
                nr_links += 1
                if 'link' in result:
                    if result['link'] == i['link']:
                        nr_correct_instances += 1
                        nr_correct_links += 1
                        row.append('1')
                    else:
                        nr_false_links += 1
                        row.append('0')
                else:
                    row.append('0')
            # A link should not be predicted
            elif i['link'] == 'none':
                if 'link' in result:
                    nr_false_links += 1
                    row.append('0')
                else:
                    nr_correct_instances += 1
                    row.append('1')

            csv_writer.writerow(row)

            nr_instances += 1

accuracy = nr_correct_instances / float(nr_instances)
link_recall = nr_correct_links / float(nr_links)
link_precision = nr_correct_links / float(nr_correct_links + nr_false_links)
link_f_measure = 2 * ((link_precision * link_recall) / float(link_precision +
        link_recall))

print '---'
print 'Number of instances: ' + str(nr_instances)
print 'Number of correct predictions: ' + str(nr_correct_instances)
print 'Prediction accuracy: ' + str(accuracy)
print '---'
print 'Number of link instances: ' + str(nr_links)
print 'Number of correct link predictions: ' + str(nr_correct_links)
print 'Link recall: ' + str(link_recall)
print '---'
print 'Number of correct link predictions: ' + str(nr_correct_links)
print 'Number of link predictions: ' + str(nr_correct_links + nr_false_links)
print 'Link precision: ' + str(link_precision)
print '---'
print 'Link F1-measure: ' + str(link_f_measure)
print '---'