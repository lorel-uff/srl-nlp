#!/bin/python
'''
Runs all the experiments in a given directory tree
'''

from os           import path, walk as walkdir
from sys          import argv
from json         import load
from regex        import compile
from subprocess   import PIPE, Popen as popen
from ConfigParser import ConfigParser
#import probfoil
import logging
import argparse


config = ConfigParser()
config.read("external.conf")

class Learner(object):
    def __init__(self, *args, **kargs):
        self.name = 'Dummy'
        self.logger = logging.getLogger(__name__)

    def run_learning(self, out_file = None, **kargs):
        assert True, 'abstract method!'

    def __repr__(self):
        return self.name

class Aleph(Learner):
    '''
    API to run the Aleph Learning Algorithm
    '''
    def __init__(self, dir, files, *args, **kargs):
        '''Initializes the Aleph API

        Params:
            dir: directory with the experiment data
            files: list of files to be selected for learning based on their extension
            prefix: [optional] consider only files with this prefix
        '''
        super(Aleph, self).__init__(*args, **kargs)
        script_config = config.get('aleph_local','script')
        self.script = kargs.get('script',script_config)
        self.name   = 'Aleph'
        self.dir    = dir
        self.prefix = kargs.get('prefix', None)
        self.logger.debug('Checking necessary files in %s', self.dir)
        #self.kb     = self._find_file(self.prefix,'pl', files)
        self.neg    = self._find_file(self.prefix, 'n', files)
        self.fact   = self._find_file(self.prefix, 'f', files)
        self.base   = self._find_file(self.prefix, 'b', files)

    def _find_file(self, prefix, extension, file_list):
        '''
        Returns the first file with the given prefix and extension.

        self._find_file(str,str,[str,...]) -> str

        Params:
            prefix: the prefix of the file name
            extension: the desired extension of the file
            file_list: the list of files to pick from
        '''
        candidates = map(lambda x: path.splitext(x), file_list)
        if len(candidates) < 1:
            self.logger.debug('No candidates')
        else:
            if prefix:
                match_prefix = filter(lambda x: x[0].startswith(prefix), candidates)
            else:
                match_prefix = candidates
            if extension:
                match_extension = filter(lambda x: x[1][1:] == extension, match_prefix)
            else:
                match_extension = match_prefix
            out = match_extension
            if len(out) > 0:
                if len(out) > 1:
                    self.logger.warning('More than one file matching the requisites %s',
                                        ', '.join(out))
                return ''.join(out[0])
            else:
                self.logger.warning('No file matching requirements: prefix ="%s", ext="%s"',
                                    prefix, extension)
                self.logger.warning('Candidates: %s...', str(file_list))
        return None

    def _has_necessary_files(self):
        '''Returns if the learner has all the files it requires to function
        '''
        return self.neg and self.fact and self.base

    def get_files(self):
        '''
        Returns a list of the relevant files for learning
        '''
        return (self.neg, self.fact, self.base)

    def get_prefix(self):
        '''
        Returns the prefix of the files used for learning
        '''
        if self.prefix:
            return self.prefix
        else:
            prefixes = map(lambda x: path.splitext(x)[0], self.get_files())
            prefixes = filter(lambda x: x, prefixes)
            if len(prefixes) > 1:
                for f in prefixes[1:]:
                    if f != prefixes[0]:
                        e = Exception('There is no unique prefix, %s' %', '.join(self.get_files()))
                        self.logger.critical(e)
                        raise e
                return prefixes[0]
            else:
                if len(prefixes) > 0:
                    return prefixes[0]
                else:
                    e = Exception('There is no prefix')
                    self.logger.critical(e)
                    raise e

    def run_learning(self, out_file_name = None, **kargs):
        ''' Calls Yap to run Aleph and process the output

            Params:
                out_file_name: [optional] name of the output file to be generated in the experiment folder
            
            If there is no out_file_name this method is going to print the output
        '''
        to_str = True if out_file_name else False
        if self._has_necessary_files():
            if out_file_name:
                out_stream = open(path.join(self.dir, out_file_name), 'w')
            else:
                out_stream = PIPE
            self.logger.debug('%s > [neg=%s, facts=%s, base=%s',
                              self.name,
                              *self.get_files())
            process_args = [self.script, self.dir, self.get_prefix()]
            self.logger.debug("Aleph process args: %s", ', '.join(process_args))
            process = popen(process_args, stdout = out_stream, stderr = PIPE)
            if out_file_name:
                out_stream.close()
            else:
                for line in process.stdout.readlines():
                    print line,
            err = process.stderr.read()
            if err:
                self.logger.warning("ALEPH STDERR:\n%s\n%s", self.dir, err)
        else:
            self.logger.debug('Empty dir: %s', self.dir)

    @staticmethod
    def process_out(in_file):
        #TODO
        out = {}
        return out


def run_tree(dir, func, prefix = None, logger = logging.getLogger(__name__)):
    _, subdir, files = walkdir(dir).next()
    #logger.debug('Running on %s', dir)
    if len(files) > 0:
        logger.debug("Files: %s", ', '.join(files))
    if len(subdir) > 0:
        for child in subdir:
            run_tree(path.join(dir,child), func, prefix, logger)
    func(dir, files, prefix, logger)

def _runAleph(dir, file_list, prefix = None, logger = logging.getLogger(__name__)):
    learner = Aleph(dir, file_list, prefix = prefix)
    learner.run_learning('out.txt')

def parse_args(argv = argv):
    parser = argparse.ArgumentParser(description = 'Runs the experiments defined in each folder (Aleph only right now)')
    parser.add_argument('dir_path', help = 'the path of the experiments')
    parser.add_argument('-p', '--file_prefix', help = 'prefix of the experiment files')
    parser.add_argument('-v', '--verbosity', action='count', default=0, help = 'increase output verbosity')
    args = parser.parse_args(argv[1:])
    return args

def config_logger(verbosity):
    '''Logger settings'''
    FORMAT = "[%(levelname)s:%(name)s:%(filename)s:%(lineno)s] %(message)s"
    if verbosity == 0:
        logging.basicConfig(level=logging.CRITICAL, format=FORMAT)
    elif verbosity == 1 :
        logging.basicConfig(level=logging.INFO, format=FORMAT)
    elif verbosity > 1:
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    logger = logging.getLogger(__name__)
    return logger


def main(argv):
    args = parse_args(argv.verbosity)
    logger = config_logger(args)

    logger.info('Starting at %s', args.dir_path)
    run_tree(args.dir_path, _runAleph, args.file_prefix)
    logger.info('Done')

if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    try:
        main(argv)
    except KeyboardInterrupt:
        logger.info('Halted by the user')
    except OSError as e:
        logger.critical('Problem reading/writing files')
        logger.exception(e)