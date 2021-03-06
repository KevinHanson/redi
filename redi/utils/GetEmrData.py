# Contributors:
# Christopher P. Barnes <senrabc@gmail.com>
# Andrei Sura: github.com/indera
# Mohan Das Katragadda <mohan.das142@gmail.com>
# Philip Chase <philipbchase@gmail.com>
# Ruchi Vivek Desai <ruchivdesai@gmail.com>
# Taeber Rapczak <taeber@ufl.edu>
# Nicholas Rejack <nrejack@ufl.edu>
# Josh Hanna <josh@hanna.io>
# Copyright (c) 2015, University of Florida
# All rights reserved.
#
# Distributed under the BSD 3-Clause License
# For full text of the BSD 3-Clause License see http://opensource.org/licenses/BSD-3-Clause

"""
This module is used to connect to an sftp server
and retrieve the raw EMR file to be used as input for RED-I.
"""

import os
import csv
from xml.sax import saxutils
import logging
import pysftp
from csv2xml import openio, Writer
from paramiko.ssh_exception import SSHException, BadAuthenticationType
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class EmrFileAccessDetails(object) :
    """
    Encapsulate the settings used to retrieve the EMR
    source file using an SFTP connection
    @see redi#_run()
    """
    def __init__(self,
            emr_download_file,
            emr_host,
            emr_username,
            emr_password,
            emr_port,
            emr_private_key,
            emr_private_key_pass
            ):

        self.download_file = emr_download_file
        self.host = emr_host
        self.username = emr_username
        self.password = emr_password
        self.port = int(emr_port)
        self.private_key = emr_private_key
        self.private_key_pass = emr_private_key_pass

#============================
# Module level functions
#============================

def download_file(destination, access_details):
    """
    Download a file from the sftp server
    :destination the name of the file which will be downloaded
    :access_details holds info for accessing the source file over sftp

    @see get_emr_data()
    """
    connection_info = dict(access_details.__dict__)
    # delete unnecessary element form the dictionary
    del connection_info['download_file']

    # check for errors during authentication with EMR server
    try:
        with pysftp.Connection(**connection_info) as sftp:
            logger.info("User %s connected to sftp server %s" % \
                (connection_info['username'], connection_info['host']))
            sftp.get(access_details.download_file, destination)
    except IOError as e:
        logger.error("Please verify that the private key file mentioned in "\
            "settings.ini exists.")
        logger.exception(e)
        sys.exit()
    except BadAuthenticationType as e:
        logger.error("Please verify that the EMR server connection details "\
            "under section emr_data in settings.ini are correct")
        logger.exception(e)
        sys.exit()
    except SSHException as e:
        logger.error("Please verify that the EMR server connection details "\
            "under section emr_data in settings.ini are correct")
        logger.exception(e)
        sys.exit()



def data_preprocessing(input_filename, output_filename):
    # replace &, >, < with &amp;, &>;, &<;
    with open(input_filename, 'r') as raw, open(output_filename, 'w') as processed:
        for line in raw:
            processed.write(saxutils.escape(line))


def generate_xml(input_filename, output_filename):

    # generate_xml now replicates the functionality from the
    # "main" code block of csv2xml.py. This allows us to use
    # it like another module in our project without having to call os.system().
    class Arguments:
        pass
    args = Arguments()

    # Set the properties which we used to pass as command line arguments
    args.iencoding = 'cp1252'
    args.oencoding = 'utf8'
    args.header = True,
    args.delimiter = ','
    args.declaration = True
    args.root_elem = 'study'
    args.record_elem = 'subject'
    args.ofile = output_filename
    args.ifile = input_filename

    # Now configure the defaults that would've been set if we were to execute
    # csv2xml.py from the command line.
    args.linebreak = u'\n'
    args.escapechar = None
    args.indent = u'    '
    args.quoting = csv.QUOTE_MINIMAL
    args.skipinitialspace = False
    args.field_elem = u'field'
    args.flat_fields = False
    args.doublequote = True
    args.quotechar = '"'
    args.newline_elem = None

    # WARNING! The rest of this function is copied verbatim from csv2xml.py.
    # There should be no differences between these blocks of code whatsoever.
    # TODO: Replace csv2xml.py entirely?
    csv.register_dialect('custom',
                         delimiter=args.delimiter,
                         doublequote=args.doublequote,
                         escapechar=args.escapechar,
                         quotechar=args.quotechar,
                         quoting=args.quoting,
                         skipinitialspace=args.skipinitialspace)
    with openio(args.ifile, mode='r', encoding=args.iencoding,
                newline='') as ifile:
        csvreader = csv.reader(ifile, dialect='custom')
        if args.header:
            args.header = next(csvreader)
        with openio(args.ofile, 'w', args.oencoding) as ofile:
            writer = Writer(ofile, args)
            writer.write_file(csvreader)

def cleanup(file_to_delete):
    os.remove(file_to_delete)

def get_emr_data(conf_dir, connection_details):
    """
    :conf_dir configuration directory name
    :connection_details EmrFileAccessDetails object
    """
    raw_txt_file = os.path.join(conf_dir, 'raw.txt')
    escaped_file = os.path.join(conf_dir, 'rawEscaped.txt')
    raw_xml_file = os.path.join(conf_dir, 'raw.xml')

    # download csv file
    download_file(raw_txt_file, connection_details)

    # replace certain characters with escape sequences
    data_preprocessing(raw_txt_file, escaped_file)

    # run csv2xml.py to generate data in xml format
    generate_xml(escaped_file, raw_xml_file)

    # delete rawEscaped.txt
    cleanup(escaped_file)

