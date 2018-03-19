#!/usr/bin/env python
import subprocess
import argparse
import os
import glob
import shutil
import csv
import time
import sys
import re

# Version
_version_ = "0.1.4"

# Argparse argument setup
parser = argparse.ArgumentParser(description="Hands free MinION data processing using Porechop for barcode trimming/binning, and Unicycler for assembly")
requiredargs = parser.add_argument_group('required arguments')
requiredargs.add_argument("-i", "--input", required=True, help="Path to CSV file containing list of barcodes and their corresponding sample name")
requiredargs.add_argument("-f", "--fastq", required=True, help="Path to directory containing raw basecalled data generated by Albacore in fastq format")
requiredargs.add_argument("-o", "--output", required=True, help="Path to output destination")
parser.add_argument("-p", "--porechop", action="store_true", help="Run Porechop and rename/collect files only (i.e. no assembly)")
parser.add_argument("-u", "--unicycler", action="store_true", help="Run Unicycler and rename/collect files only (i.e. no adapter trimming)")
parser.add_argument("-hyb", "--hybrid", action="store_true", help="Specifies hybrid assembly, expects input file to contain filenames of paired end illumina reads" )
parser.add_argument("-s", "--sbs", help="Path to directory containing Illumina read files")
parser.add_argument("-c", "--call", action="store_true", help="Invoke porechop on reads identified as 'Unclassified' by Albacore")
parser.add_argument("-m", "--merge", action="store_true", help="Merges 'Unclassified' reads succesfully demultiplexed by Porechop with consensus read files")
parser.add_argument("-cons", "--conservative", action="store_true", help="Runs unicycler in conservative mode")
parser.add_argument("-bold", "--bold", action="store_true", help="Runs unicycler in bold mode")
parser.add_argument("-r", "--remove", action="store_true", help="Removes intermediate files")
args = parser.parse_args()

# Colour set up
class colours:
    warning = '\033[91m'
    blue = '\033[94m'
    invoking = '\033[93m'
    bold = '\033[1m'
    term = '\033[0m'

# Logger set up
ansi_rm = re.compile(r'\x1b\[[0-9;]*m')
class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("PoreCycler.log", "w")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(re.sub(ansi_rm, '', message))

sys.stdout = Logger()

# Hybrid syntax check
if args.hybrid and args.sbs is None:
    print colours.warning + ''
    print 'You have chosen a hybrid assembly.'
    print ''
    print 'Please supply the path to your Illumina files using -s <path>'
    print '' + colours.term
    sys.exit(1)

# Bold/Cons conflict check
if args.conservative and args.bold:
    print colours.warning + ''
    print 'You have requested both a conservative and bold unicycler run.'
    print ''
    print 'Please choose only one option'
    print '' + colours.term
    sys.exit(1)

# Porechop/Unicycler only conflict check
if args.conservative and args.bold:
    print colours.warning + ''
    print 'You have requested to run ONLY Porechop and ONLY Unicycler.'
    print ''
    print 'If this is intentional, please note that this is the default run mode.'
    print "Remove both the '-p' and '-u' flags and retry."
    print ''
    print ''
    print 'If you want to run either Porechop or Unicycler ONLY please choose only one option'
    print '' + colours.term
    sys.exit(1)

# Repetitive element definitions
def scriptfail():
    print ''
    print colours.bold + '#############'
    print 'Script Failed'
    print '#############'+ colours.term

def csverror():
    print ''
    print colours.warning + colours.bold + "Unexpected item in bagging area!" + colours.term
    time.sleep(1)
    print ''
    print ''
    print colours.warning + 'Text file contains more or less than four columns.'
    print ''
    print 'You have used the option for a hybrid assembly, your input file should be formatted like so:'
    print 'NBXX, Sample_ID, Illumina_R1, Illumina R2'
    print ''
    print 'If you are attempting to use MinION reads only, do not use the -hyb flag'
    print ''
    print 'If your input file contains the correct information, column 4 may be followed by a trailing comma'
    print 'e.g "A, B, C, D," - please change it to "A, B, C, D" and try again.'

# Welcome message:
print ''
print ''
print colours.bold + '######################'
print 'Welcome to PoreCycler!'
print '######################' + colours.term
time.sleep(1)
print ''

# Create output directory if it doesn't exist:
if not os.path.exists(args.output):
    os.mkdir(args.output)
    print 'Output directory created.'

# Directory orientation
invoked_from = os.getcwd()
os.chdir(args.fastq)
target_path = os.getcwd()
os.chdir(invoked_from)
os.chdir(args.output)
out_path = os.getcwd()
os.chdir(invoked_from)
print ''
print colours.blue + "Invoked from: " + colours.term,
print invoked_from
print ''
print colours.blue + "MinION reads in: " + colours.term,
print target_path
if args.hybrid:
    os.chdir(args.sbs)
    sbspath = os.getcwd()
    os.chdir(invoked_from)
    print ''
    print colours.blue + 'Illumina reads in: ' + colours.term,
    print sbspath
print ''
print colours.blue + "Output path: " + colours.term,
print out_path
time.sleep(1)

# Blanket if statement to split unicycler only mode.
if not args.unicycler:
    # Import barcodes + sample names + illumina file names (hybrid mode)
    print ''
    print ''
    print colours.invoking + 'Processing input csv...' + colours.term
    time.sleep(1)
    if args.hybrid:
        try:
            with open(args.input, 'rbU') as f:
                reader = csv.reader(f, skipinitialspace=True, delimiter=',')
                a, b, c, d = zip(*reader)
                barcodes = list(a)
                samples = list(b)
                Ill_R1 = list(c)
                Ill_R2 = list(d)
                print ''
                print colours.blue + "Loaded barcodes:" + colours.term,
                print barcodes
                print ''
                print ''
                print colours.blue + "Loaded samples" + colours.term,
                print samples
                print ''
                print ''
                print colours.blue + "Loaded Illumina R1:" + colours.term,
                print Ill_R1
                print colours.blue + "Loaded Illumina R2:" + colours.term,
                print Ill_R2
                time.sleep(2)
                print ''
                print ''
        except ValueError as e:
            print ''
            csverror()
            print e
            print ''
            print '#I2'
            scriptfail()
            sys.exit(1)

    # Import barcodes + sample names only
    if not args.hybrid:
            try:
                with open(args.input, 'rbU') as f:
                    reader = csv.reader(f, skipinitialspace=True, delimiter=',')
                    a, b = zip(*reader)
                    barcodes = list(a)
                    samples = list(b)
                    print ''
                    print ''
                    print colours.blue + 'Loaded barcodes:' + colours.term
                    print barcodes
                    print ''
                    print ''
                    print colours.blue + 'Loaded samples:' + colours.term
                    print samples
                    time.sleep(1)
                    print ''
                    print ''
                    print colours.warning + colours.bold + '########'
                    print 'WARNING!'
                    print '########'
                    print ''
                    print ''
                    time.sleep(1)
                    print colours.warning + 'No Illumina reads provided...' + colours.term
                    print ''
                    time.sleep(2)
                    print 'Continuing without hybrid assembly in:'
                    print '3...'
                    time.sleep(1)
                    print '2...'
                    time.sleep(1)
                    print '1...'
                    time.sleep(2)
                    print ''
                    print colours.bold + '##################################'
                    print 'Proceeding without hybrid assembly'
                    print '##################################' + colours.term
                    time.sleep(2)
            except ValueError as e:
                        print ''
                        csverror()
                        print ''
                        print (e)
                        print ''
                        print '#I1'
                        print ''
                        scriptfail()
                        sys.exit(1)

    # Create directory in output destination for raw concatenated fastq's
    catfastq = out_path + '/raw_fastqs'
    if not os.path.exists(catfastq):
        os.mkdir(catfastq);
        print ''
        print colours.blue + "Created directory:" + colours.term,
        print catfastq
        print ''
        time.sleep(1)
    else:
        print ''
        print colours.blue + 'Raw fastqs will be concatenated and placed in:' + colours.term,
        print catfastq
        print ''
        time.sleep(1)

    # Create directory in output destination for collected porechopped reads
    porechoppedreads = out_path + '/porechopped'
    if not os.path.exists(porechoppedreads):
        os.mkdir(porechoppedreads);
        print ''
        print colours.blue + "Created directory:" + colours.term,
        print ''
    print colours.blue + 'Porechopped fastqs will be placed in:' + colours.term,
    print porechoppedreads
    print ''
    time.sleep(1)

    # Generate lists for fastq generation
    sample_numbers = [x.split('B')[1] for x in barcodes]
    albacore_directories = [target_path + '/barcode' + x for x in sample_numbers]
    albacore_wildcard = [x + '/' for x in albacore_directories]
    raw_cat_fastq_names = [x + '_' + y + '.fastq' for x, y in zip(samples, barcodes)]
    catdestination = str(catfastq)
    rawfastqs = [catdestination + '/' + x for x in raw_cat_fastq_names]

    # Generate path to Illumina reads
    if args.hybrid:
        Illumina_R1 = [sbspath + '/' + x for x in Ill_R1]
        Illumina_R2 = [sbspath + '/' + x for x in Ill_R2]

    # Progression message
    print colours.bold + '######################'
    print 'Processing Input Files'
    print '######################' + colours.term
    time.sleep(2)

    # Concatenate multiple albacore output fastq into single logically named file
    print ''
    print colours.invoking + 'Concatenating Reads...' + colours.term
    print ''
    for index, directory in enumerate(albacore_wildcard):
        output_fastqs = rawfastqs[index]
        for filename in os.listdir(directory):
            fullpath = os.path.join(directory, filename)
            with open(fullpath, 'r') as opt1:
                with open(output_fastqs, 'a') as opt2:
                    opt2.write(opt1.read())
    print ''
    print 'Done!'
    print ''
    time.sleep(1)
    print ''

    # Cat unclassified reads
    if args.merge:
        unclassifiedinput = [target_path + '/unclassified/']
        catunclass = ['unclassified.fastq']
        unclassporechopout = (catdestination + '/unclassified_porechop')
        unclassoutput = (unclassporechopout + '/unclassified.fastq')
        if not os.path.exists(unclassporechopout):
            os.mkdir(unclassporechopout)
        print colours.invoking + 'Concatenating Unclassified Reads...' + colours.term
        print ''
        for directory in unclassifiedinput:
            for filename in os.listdir(directory):
                fullpath = os.path.join(directory, filename)
                with open(fullpath, 'r') as opt1:
                    with open(unclassoutput, 'a') as opt2:
                        opt2.write(opt1.read())
        print ''
        print 'Done!'
        print ''
        print ''
        time.sleep(2)

    # Porechop list generation
    porechopout = [catdestination + '/' + x + '_porechopped' for x in sample_numbers]
    porechopsamples = ['BC' + x + '.fastq' for x in sample_numbers]
    pathedporechopsamples = [x + '/' + y for x, y in zip(porechopout, porechopsamples)]

    # Invoke porechop on concatenated fastqs
    print colours.bold + '######################'
    print 'Proceeding to Porechop'
    print '######################' + colours.term
    time.sleep(2)
    print ''
    print ''
    print colours.invoking + 'Invoking porechop...' + colours.term
    print ''
    time.sleep(1)
    try:
        for opt1, opt2 in zip(rawfastqs, porechopout):
            subprocess.check_call(['porechop', '-i', opt1, '-b', opt2])
    except Exception as e:
        print colours.warning + ''
        print 'Porechop failed to run'
        print ''
        print (e)
        print '#P1'
        print ''
        print 'Check output logs to troubleshoot'
        print ''
        scriptfail()
        sys.exit(1)

    # List creation
    finalchoppedreads = [porechoppedreads + '/' + x for x in raw_cat_fastq_names]

    # Default (i.e. no merge) fastq collection and rename.
    if not args.merge:
        try:
            for opt1, opt2 in zip(pathedporechopsamples, finalchoppedreads):
                shutil.copyfile(opt1, opt2)
        except Exception as e:
            print ''
            print colours.warning + 'Failed to copy and rename reads.'
            print ''
            print (e)
            print '#F1'
            print ''
            scriptfail()
            sys.exit(1)
        print ''
        print colours.blue + 'Porechopped files succesfully renamed and written to: ' + colours.term,
        print porechoppedreads
        print ''

    # Invoke porechop on unclassified reads
    if args.merge:
        unclasspath = (out_path + '/unclassified/unclassified.fastq')
        unclassifiedchoppedoutput = [unclassporechopout + "/" + x for x in porechopsamples]
        unclassifiedsamples = ['UC' + x + '.fastq' for x in sample_numbers]
        unclassifiedsampledestination = [unclassporechopout + "/" + x for x in unclassifiedsamples]
        try:
            subprocess.check_call(['porechop', '-i', unclassoutput, '-b', unclassporechopout])
        except Exception as e:
            print colours.warning + ''
            print 'Failed to invoke porechop on unclassified reads'
            print (e)
            print ''
            print '#E20'
            scriptfail()
            sys.exit(1)
        print ''
        print colours.blue + 'Unclassified files succesfully porechopped and written to: ' + colours.term,
        print unclassporechopout
        print ''

    # If merge flag present, merge unclassified and consensus reads.
    if args.merge and args.call:
        for opt1, opt2 in zip(unclassifiedchoppedoutput, unclassifiedsampledestination):
            try:
                shutil.copyfile(opt1, opt2)
            except IOError as e:
                print ''
                print colours.warning + 'Failed to rename consensus reads.'
                print ''
                print 'The following files were not found:'
                print (e)
                print ''
                print 'Porechop may not have identified any reads matching your barcodes in Albacores unclassified output'
                print ''
                print '#C2'
                print ''
                print colours.bold + '############'
                print 'Merge Failed'
                print '############' + colours.term
        print ''
        print colours.blue + 'Porechopped files succesfully renamed and written to: ' + colours.term,
        print porechoppedreads
        print ''

        # cat unclasssampdest + porechoppedreads >> finalchoppedreads
        print colours.invoking + 'Concatenating Reads...' + colours.term
        print ''
        for file1, file2, fileout in zip(pathedporechopsamples,unclassifiedsampledestination, finalchoppedreads):
            try:
                with open (file1, 'r') as in1:
                    with open (file2, 'r') as in2:
                        with open (fileout, 'a') as out:
                            out.write(in1.read())
                            out.write(in2.read())
                            print '.',
            except Exception as e:
                print ''
                print 'Failed to locate or read Porechop output.'
                print ''
                print (e)
                print ''
                print 'Check porechop log to troubleshoot.'
                print ''
                scriptfail()
                sys.exit(1)
        print ''
        print ''
        print colours.blue + 'Merged files succesfully written to: ' + colours.term,
        print porechoppedreads
        print ''

    # Porechop completion and exit (-p)
    if args.porechop:
        print colours.invoking + colours.bold + ''
        print 'Porechop completed successfully!'
        print '' + colours.term
        print ''
        time.sleep(2)
        print ''
        print ''
        print 'Author: www.github.com/stevenjdunn'
        print ''
        print colours.bold + ''
        print '####################'
        print 'PoreCycler Complete!'
        print '####################' + colours.term
        print ''
        exit(1)

    # Porechop completion and continuation
    print colours.invoking + colours.bold + ''
    print 'Porechop completed successfully!'
    print '' + colours.term
    print ''
    time.sleep(2)
    print ''
    print colours.bold + '######################'
    print 'Proceeding to Assembly'
    print '######################' + colours.term
    print ''
    print ''

    # Invoke unicycler
    unipath = (out_path + '/unicycler/')
    if not os.path.exists(unipath):
        os.mkdir(unipath)
        print colours.blue + 'Unicycler output will be written to: ' + colours.term,
        print unipath
    else:
        print colours.blue + 'Unicycler output will be placed in: ' + colours.term,
        print unipath
    unioutdirs = [unipath + x + '_' + y for x, y in zip(samples, barcodes)]
    print ''
    print ''
    print colours.invoking + 'Invoking Unicycler...' + colours.term
    print ''
    time.sleep(1)

    # Long read only
    if not args.hybrid and not args.conservative and not args.bold:
        try:
            for opt1, opt2 in zip(finalchoppedreads, unioutdirs):
                subprocess.check_call(['unicycler', '-l', opt1, '-o', opt2])
        except Exception as e:
                        print ''
                        print colours.warning + 'Failed to invoke Unicycler.'
                        print ''
                        print (e)
                        print ''
                        print 'Check logs to troubleshoot. #E1'
                        print ''
                        scriptfail()
                        sys.exit(1)

    # Long read + conservative
    if args.conservative and not args.hybrid:
        try:
            for opt1, opt2 in zip(finalchoppedreads, unioutdirs):
                subprocess.check_call(['unicycler', '--mode', 'conservative','-l', opt1, '-o', opt2])
        except Exception as e:
                        print ''
                        print colours.warning + 'Failed to invoke Unicycler.'
                        print ''
                        print (e)
                        print ''
                        print 'Check logs to troubleshoot. #E2'
                        print ''
                        scriptfail()
                        sys.exit(1)

    # Long read + bold
    if args.bold and not args.hybrid:
        try:
            for opt1, opt2 in zip(finalchoppedreads, unioutdirs):
                subprocess.check_call(['unicycler', '--mode', 'bold','-l', opt1, '-o', opt2])
        except Exception as e:
                        print ''
                        print colours.warning + 'Failed to invoke Unicycler.'
                        print ''
                        print (e)
                        print ''
                        print 'Check logs to troubleshoot. #E3'
                        print ''
                        scriptfail()
                        sys.exit(1)
    # Hybrid only
    if args.hybrid and not args.conservative and not args.bold:
        try:
            for opt1, opt2, opt3, opt4 in zip(finalchoppedreads, Illumina_R1, Illumina_R2, unioutdirs):
                subprocess.check_call(['unicycler', '-1', opt2, '-2', opt3, '-l', opt1, '-o', opt4])
        except Exception as e:
                        print ''
                        print colours.warning + 'Failed to invoke Unicycler.'
                        print ''
                        print (e)
                        print ''
                        print 'Check logs to troubleshoot. #E4'
                        print ''
                        scriptfail()
                        sys.exit(1)

    # Hybrid + conservative
    if args.hybrid and args.conservative:
        try:
            for opt1, opt2, opt3, opt4 in zip(finalchoppedreads, Illumina_R1, Illumina_R2, unioutdirs):
                subprocess.check_call(['unicycler', '--mode', 'conservative', '-1', opt2, '-2', opt3, '-l', opt1, '-o', opt4])
        except Exception as e:
                        print ''
                        print colours.warning + 'Failed to invoke Unicycler.'
                        print ''
                        print (e)
                        print ''
                        print 'Check logs to troubleshoot. #E5'
                        print ''
                        scriptfail()
                        sys.exit(1)

    # Hybrid + bold
    if args.hybrid and args.bold:
        try:
            for opt1, opt2, opt3, opt4 in zip(finalchoppedreads, Illumina_R1, Illumina_R2, unioutdirs):
                subprocess.check_call(['unicycler', '--mode', 'bold', '-1', opt2, '-2', opt3, '-l', opt1, '-o', opt4])
        except Exception as e:
                        print ''
                        print colours.warning + 'Failed to invoke Unicycler.'
                        print ''
                        print (e)
                        print ''
                        print 'Check logs to troubleshoot. #E6'
                        print ''
                        scriptfail()
                        sys.exit(1)

    # Unicycler completion message
    print ''
    print ''
    print colours.invoking + colours.bold + 'Unicycler completed successfully!' + colours.term
    print ''
    time.sleep(3)

    # Path generation
    graphs = [x + '/assembly.gfa' for x in unioutdirs]
    assemblies = [x + '/assembly.fasta' for x in unioutdirs]
    logs = [x + '/unicycler.log' for x in unioutdirs]
    graph_path = (out_path + '/assembly_graphs')
    assembly_path = (out_path + '/assembly_fasta')
    log_path = (out_path + '/assembly_logs')
    if not os.path.exists(graph_path):
        os.mkdir(graph_path)
    if not os.path.exists(assembly_path):
        os.mkdir(assembly_path)
    if not os.path.exists(log_path):
        os.mkdir(log_path)
    graph_target = [graph_path + '/' + x + '_' + y + '_graph.gfa' for x, y in zip(samples, barcodes)]
    assemblies_target = [assembly_path + '/' + x + '_' + y + '.fasta' for x, y in zip(samples, barcodes)]
    logs_target = [log_path + '/' + x + '_' + y + '_unicycler.log' for x, y in zip(samples, barcodes)]

# Unicycler only mode
if args.unicycler:
    # Import barcodes + sample names + illumina file names (hybrid mode)
    print ''
    print ''
    print colours.invoking + 'Processing input csv...' + colours.term
    time.sleep(1)
    if args.hybrid:
        try:
            with open(args.input, 'rbU') as f:
                reader = csv.reader(f, skipinitialspace=True, delimiter=',')
                a, b, c, d = zip(*reader)
                samples = list(a)
                Min_R = list(b)
                Ill_R1 = list(c)
                Ill_R2 = list(d)
                print ''
                print colours.blue + "Loaded sample names:" + colours.term,
                print samples
                print ''
                print ''
                print colours.blue + "Loaded MinION read filenames:" + colours.term,
                print Min_R
                print ''
                print ''
                print colours.blue + "Loaded Illumina R1 filenames:" + colours.term,
                print Ill_R1
                print colours.blue + "Loaded Illumina R2 filenames:" + colours.term,
                print Ill_R2
                time.sleep(2)
                print ''
                print ''
        except ValueError as e:
            print ''
            csverror()
            print e
            print ''
            print '#IU1'
            scriptfail()
            sys.exit(1)

    # Import barcodes + sample names only
    if not args.hybrid:
            try:
                with open(args.input, 'rbU') as f:
                    reader = csv.reader(f, skipinitialspace=True, delimiter=',')
                    a, b = zip(*reader)
                    samples = list(a)
                    Min_R = list(b)
                    print ''
                    print ''
                    print colours.blue + 'Loaded sample names:' + colours.term
                    print barcodes
                    print ''
                    print ''
                    print colours.blue + 'Loaded Minion read filenames:' + colours.term
                    print Min_R
                    time.sleep(1)
                    print ''
                    print ''
                    print colours.warning + colours.bold + '########'
                    print 'WARNING!'
                    print '########'
                    print ''
                    print ''
                    time.sleep(1)
                    print colours.warning + 'No Illumina reads provided...' + colours.term
                    print ''
                    time.sleep(2)
                    print 'Continuing without hybrid assembly in:'
                    print '3...'
                    time.sleep(1)
                    print '2...'
                    time.sleep(1)
                    print '1...'
                    time.sleep(2)
                    print ''
                    print colours.bold + '##################################'
                    print 'Proceeding without hybrid assembly'
                    print '##################################' + colours.term
                    time.sleep(2)
            except ValueError as e:
                        print ''
                        csverror()
                        print ''
                        print (e)
                        print ''
                        print '#IU2'
                        print ''
                        scriptfail()
                        sys.exit(1)
    # List Generation
    unipath = (out_path + '/unicycler/')
    unioutdirs = [unipath + x for x in samples]
    Minion_in = [target_path + '/' + x for x in Min_R]
    if args.hybrid:
        Illumina_R1 = [sbspath + '/' + x for x in Ill_R1]
        Illumina_R2 = [sbspath + '/' + x for x in Ill_R2]
    graphs = [x + '/assembly.gfa' for x in unioutdirs]
    assemblies = [x + '/assembly.fasta' for x in unioutdirs]
    logs = [x + '/unicycler.log' for x in unioutdirs]
    graph_path = (out_path + '/assembly_graphs')
    assembly_path = (out_path + '/assembly_fasta')
    log_path = (out_path + '/assembly_logs')
    if not os.path.exists(graph_path):
        os.mkdir(graph_path)
    if not os.path.exists(assembly_path):
        os.mkdir(assembly_path)
    if not os.path.exists(log_path):
        os.mkdir(log_path)
    graph_target = [graph_path + '/' + x + '_graph.gfa' for x in samples]
    assemblies_target = [assembly_path + '/' + x + '.fasta' for x in samples]
    logs_target = [log_path + '/' + x + '_unicycler.log' for x in samples]

    # Invoke unicycler
    if not os.path.exists(unipath):
        os.mkdir(unipath)
    print colours.blue + 'Unicycler output will be written to: ' + colours.term,
    print unipath
    print ''
    print ''
    print colours.invoking + 'Invoking Unicycler...' + colours.term
    print ''
    time.sleep(1)

    # Long read only
    if not args.hybrid and not args.conservative and not args.bold:
        try:
            for opt1, opt2 in zip(Minion_in, unioutdirs):
                subprocess.check_call(['unicycler', '-l', opt1, '-o', opt2])
        except Exception as e:
                        print ''
                        print colours.warning + 'Failed to invoke Unicycler.'
                        print ''
                        print (e)
                        print ''
                        print 'Check logs to troubleshoot. #E1'
                        print ''
                        scriptfail()
                        sys.exit(1)

    # Long read + conservative
    if args.conservative and not args.hybrid:
        try:
            for opt1, opt2 in zip(Minion_in, unioutdirs):
                subprocess.check_call(['unicycler', '--mode', 'conservative','-l', opt1, '-o',opt2])
        except Exception as e:
                        print ''
                        print colours.warning + 'Failed to invoke Unicycler.'
                        print ''
                        print (e)
                        print ''
                        print 'Check logs to troubleshoot. #E2'
                        print ''
                        scriptfail()
                        sys.exit(1)

    # Long read + bold
    if args.bold and not args.hybrid:
        try:
            for opt1, opt2 in zip(Minion_in, unioutdirs):
                subprocess.check_call(['unicycler', '--mode', 'bold','-l', opt1, '-o', opt2])
        except Exception as e:
                        print ''
                        print colours.warning + 'Failed to invoke Unicycler.'
                        print ''
                        print (e)
                        print ''
                        print 'Check logs to troubleshoot. #E3'
                        print ''
                        scriptfail()
                        sys.exit(1)

    # Hybrid only
    if args.hybrid and not args.conservative and not args.bold:
        try:
            for opt1, opt2, opt3, opt4 in zip(Minion_in, Illumina_R1, Illumina_R2, unioutdirs):
                subprocess.check_call(['unicycler', '-1', opt2, '-2', opt3, '-l', opt1, '-o', opt4])
        except Exception as e:
                        print ''
                        print colours.warning + 'Failed to invoke Unicycler.'
                        print ''
                        print (e)
                        print ''
                        print 'Check logs to troubleshoot. #E4'
                        print ''
                        scriptfail()
                        sys.exit(1)

    # Hybrid + conservative
    if args.hybrid and args.conservative:
        try:
            for opt1, opt2, opt3, opt4 in zip(Minion_in, Illumina_R1, Illumina_R2, unioutdirs):
                subprocess.check_call(['unicycler', '--mode', 'conservative', '-1', opt2, '-2', opt3, '-l', opt1, '-o', opt4])
        except Exception as e:
                        print ''
                        print colours.warning + 'Failed to invoke Unicycler.'
                        print ''
                        print (e)
                        print ''
                        print 'Check logs to troubleshoot. #E5'
                        print ''
                        scriptfail()
                        sys.exit(1)

    # Hybrid + bold
    if args.hybrid and args.bold:
        try:
            for opt1, opt2, opt3, opt4 in zip(Minion_in, Illumina_R1, Illumina_R2, unioutdirs):
                subprocess.check_call(['unicycler', '--mode', 'bold', '-1', opt2, '-2', opt3, '-l', opt1, '-o', opt4])
        except Exception as e:
                        print ''
                        print colours.warning + 'Failed to invoke Unicycler.'
                        print ''
                        print (e)
                        print ''
                        print 'Check logs to troubleshoot. #E6'
                        print ''
                        scriptfail()
                        sys.exit(1)

    # Unicycler completion message
    print ''
    print ''
    print colours.invoking + colours.bold + 'Unicycler completed successfully!' + colours.term
    print ''
    time.sleep(3)


# Rename and collect assemblies
for opt1, opt2 in zip(assemblies, assemblies_target):
    shutil.copyfile(opt1, opt2)
print ''
print colours.blue + 'Assemblies renamed and placed in: ' + colours.term,
print assembly_path

# Rename and collect graphs
for opt1, opt2 in zip(graphs, graph_target):
    shutil.copyfile(opt1, opt2)
print ''
print colours.blue + 'Assembly graphs renamed and placed in: ' + colours.term,
print graph_path

# Rename and collect logs
for opt1, opt2 in zip(logs, logs_target):
    shutil.copyfile(opt1, opt2)
print ''
print colours.blue + 'Unicycler logs renamed and placed in: ' + colours.term,
print log_path

# Remove intermediate files
if args.remove:
    print ''
    print colours.invoking + 'Removing intermediate files...'
    print '' + colours.term
    shutil.rmtree(catfastq)

# DONE:
    # Test Unicycler only pathway (hyb default, bold)

# Immediate future plans:
    # Test Cons, Bold Long only pathways
    # Test hybrid cons pathway
    # Strip weird BOM encoding from CSVs

# Possible future plans:
    # Parse unicycler output logs to detect errors.
    # Create summary report with assembly metrics.
    # Write output file containing final read names for use in assembly only argument.

# Script ending
print ''
print ''
print 'Author: www.github.com/stevenjdunn'
print ''
print colours.bold + ''
print '####################'
print 'PoreCycler Complete!'
print '####################' + colours.term
