#!/usr/bin/env python

# encoding: utf-8
"""
tophat.py

Created by Cole Trapnell on 2008-12-25.
Copyright (c) 2008 Cole Trapnell. All rights reserved.
Updated and maintained by Daehwan Kim and Geo Pertea since Jul 2010.
"""
import sys
try:
    import psyco
    psyco.full()
except ImportError:
    pass

import getopt
import subprocess
import errno
import os
import warnings
import re
import glob
import signal
from datetime import datetime
from shutil import copy, rmtree, move
import logging

use_message = '''
TopHat maps short sequences from spliced transcripts to whole genomes.

Usage:
    tophat [options] <bowtie_index> <reads1[,reads2,...]> [reads1[,reads2,...]] \\
                                    [quals1,[quals2,...]] [quals1[,quals2,...]]

Options:
    -v/--version
    -o/--output-dir                <string>    [ default: ./tophat_out         ]
    --bowtie1                                  [ default: bowtie2              ]
    -N/--read-mismatches           <int>       [ default: 2                    ]
    --read-gap-length              <int>       [ default: 2                    ]
    --read-edit-dist               <int>       [ default: 2                    ]
    --read-realign-edit-dist       <int>       [ default: "read-edit-dist" + 1 ]
    -a/--min-anchor                <int>       [ default: 8                    ]
    -m/--splice-mismatches         <0-2>       [ default: 0                    ]
    -i/--min-intron-length         <int>       [ default: 50                   ]
    -I/--max-intron-length         <int>       [ default: 500000               ]
    -g/--max-multihits             <int>       [ default: 20                   ]
    --suppress-hits
    -x/--transcriptome-max-hits    <int>       [ default: 60                   ]
    -M/--prefilter-multihits                   ( for -G/--GTF option, enable
                                                 an initial bowtie search
                                                 against the genome )
    --max-insertion-length         <int>       [ default: 3                    ]
    --max-deletion-length          <int>       [ default: 3                    ]
    --solexa-quals
    --solexa1.3-quals                          (same as phred64-quals)
    --phred64-quals                            (same as solexa1.3-quals)
    -Q/--quals
    --integer-quals
    -C/--color                                 (Solid - color space)
    --color-out
    --library-type                 <string>    (fr-unstranded, fr-firststrand,
                                                fr-secondstrand)
    -p/--num-threads               <int>       [ default: 1                   ]
    -R/--resume                    <out_dir>   ( try to resume execution )
    -G/--GTF                       <filename>  (GTF/GFF with known transcripts)
    --transcriptome-index          <bwtidx>    (transcriptome bowtie index)
    -T/--transcriptome-only                    (map only to the transcriptome)
    -j/--raw-juncs                 <filename>
    --insertions                   <filename>
    --deletions                    <filename>
    -r/--mate-inner-dist           <int>       [ default: 50                  ]
    --mate-std-dev                 <int>       [ default: 20                  ]
    --no-novel-juncs
    --no-novel-indels
    --no-gtf-juncs
    --no-coverage-search
    --coverage-search
    --microexon-search
    --keep-tmp
    --tmp-dir                      <dirname>   [ default: <output_dir>/tmp ]
    -z/--zpacker                   <program>   [ default: gzip             ]
    -X/--unmapped-fifo                         [use mkfifo to compress more temporary
                                                 files for color space reads]

Advanced Options:
    --report-secondary-alignments
    --no-discordant
    --no-mixed

    --segment-mismatches           <int>       [ default: 2                ]
    --segment-length               <int>       [ default: 25               ]

    --bowtie-n                                 [ default: bowtie -v        ]
    --min-coverage-intron          <int>       [ default: 50               ]
    --max-coverage-intron          <int>       [ default: 20000            ]
    --min-segment-intron           <int>       [ default: 50               ]
    --max-segment-intron           <int>       [ default: 500000           ]
    --no-sort-bam                              (Output BAM is not coordinate-sorted)
    --no-convert-bam                           (Do not output bam format.
                                                Output is <output_dir>/accepted_hits.sam)
    --keep-fasta-order
    --allow-partial-mapping

Bowtie2 related options:
  Preset options in --end-to-end mode (local alignment is not used in TopHat2)
    --b2-very-fast
    --b2-fast
    --b2-sensitive
    --b2-very-sensitive

  Alignment options
    --b2-N                         <int>       [ default: 0                ]
    --b2-L                         <int>       [ default: 20               ]
    --b2-i                         <func>      [ default: S,1,1.25         ]
    --b2-n-ceil                    <func>      [ default: L,0,0.15         ]
    --b2-gbar                      <int>       [ default: 4                ]

  Scoring options
    --b2-mp                        <int>,<int> [ default: 6,2              ]
    --b2-np                        <int>       [ default: 1                ]
    --b2-rdg                       <int>,<int> [ default: 5,3              ]
    --b2-rfg                       <int>,<int> [ default: 5,3              ]
    --b2-score-min                 <func>      [ default: L,-0.6,-0.6      ]

  Effort options
    --b2-D                         <int>       [ default: 15               ]
    --b2-R                         <int>       [ default: 2                ]

Fusion related options:
    --fusion-search
    --fusion-anchor-length         <int>       [ default: 20               ]
    --fusion-min-dist              <int>       [ default: 10000000         ]
    --fusion-read-mismatches       <int>       [ default: 2                ]
    --fusion-multireads            <int>       [ default: 2                ]
    --fusion-multipairs            <int>       [ default: 2                ]
    --fusion-ignore-chromosomes    <list>      [ e.g, <chrM,chrX>          ]

    --fusion-do-not-resolve-conflicts          [this is for test purposes  ]

SAM Header Options (for embedding sequencing run metadata in output):
    --rg-id                        <string>    (read group ID)
    --rg-sample                    <string>    (sample ID)
    --rg-library                   <string>    (library ID)
    --rg-description               <string>    (descriptive string, no tabs allowed)
    --rg-platform-unit             <string>    (e.g Illumina lane ID)
    --rg-center                    <string>    (sequencing center name)
    --rg-date                      <string>    (ISO 8601 date of the sequencing run)
    --rg-platform                  <string>    (Sequencing platform descriptor)
'''

# Deprecated:
#    --min-closure-exon             <int>       [ default: 100              ]
#    --min-closure-intron           <int>       [ default: 50               ]
#    --max-closure-intron           <int>       [ default: 5000             ]
#    --no-closure-search
#    --closure-search
#    --butterfly-search
#    --no-butterfly-search
#    -F/--min-isoform-fraction      <float>     [ default: 0.15             ]

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

output_dir = "./tophat_out/"
logging_dir = output_dir + "logs/"
run_log = None
tophat_log = None  #main log file handle
tophat_logger = None # main logging object
run_cmd = None
tmp_dir = output_dir + "tmp/"
bin_dir = sys.path[0] + "/"
use_zpacker = False # this is set by -z/--zpacker option (-z0 leaves it False)

use_BAM_Unmapped = False # automatically set to True for non-Solid reads, handles unmapped reads in BAM format

use_BWT_FIFO = False # can only be set to True if use_zpacker is True and only with -C/--color
# enabled by -X/-unmapped-fifo option (unless -z0)
unmapped_reads_fifo = None # if use_BWT_FIFO is True, this tricks bowtie into writing the
                           # unmapped reads into a compressed file

samtools_path = "samtools_0.1.18"
bowtie_path = None
fail_str = "\t[FAILED]\n"
gtf_juncs = None #file name with junctions extracted from given GFF file

# version of GFF transcriptome parser accepted for pre-built transcriptome indexes
# TopHat will automatically rebuild a transcriptome index if the version
#   found in the {transcriptome_index}.ver file is lower than this value
# -do NOT increment this unless you want TopHat to force a rebuild of all users' transcriptome indexes!
GFF_T_VER = 209 #GFF parser version

#mapping types:

_reads_vs_G, _reads_vs_T, _segs_vs_G, _segs_vs_J = range(1,5)

# execution resuming stages (for now, execution can be resumed only for stages
# after the pre-filter and transcriptome searches):
_stage_prep, _stage_map_start, _stage_map_segments, _stage_find_juncs, _stage_juncs_db, _stage_map2juncs, _stage_tophat_reports, _stage_alldone = range(1,9)
stageNames = ["start", "prep_reads", "map_start", "map_segments", "find_juncs", "juncs_db", "map2juncs", "tophat_reports", "alldone"]
#                0           1               2            3           4                5          6           7          ,    8
runStages = dict([(stageNames[st], st) for st in range(0, 9)])
currentStage  = 0
resumeStage = 0

def getResumeStage(rlog):
  #returns tuple: (resumeStage, old_cmd_args)
  oldargv = None
  try:
    flog=open(rlog)
    #first line must be the actual tophat command used
    thcmd=None
    try:
        thcmd = flog.next()
    except StopIteration:
        die("Error: cannot resume, run.log is empty.")
    oldargv=thcmd.split()
    resume_tag = None
    for line in flog:
       #scan for last resume code, if any
       r=re.match("^#>(\w+):$", line)
       if r:
          resume_tag=r.group(1)
    #global resumeStage
    if resume_tag:
       if resume_tag in runStages:
          resume_stage = runStages[resume_tag]
       else:
          die("Error: unrecognized run stage '"+resume_tag+"'")
    else:
       die("Error: resuming requested but no valid stage found in run.log")
    flog.close()
  except IOError:
    die("Error: cannot resume, failed to open "+rlog)
  return (resume_stage, oldargv)

def doResume(odir):
  #must return the original list of arguments
  rlog = odir+"/logs/run.log"
  rstage = 0
  rargv = None
  r0log = odir+"/logs/run.resume0.log"
  r0stage = 0
  r0argv = None
  if fileExists(r0log):
     r0stage, r0argv = getResumeStage(r0log)
  else:
     if fileExists(rlog, 10):
       copy(rlog, r0log)
  rstage, rargv = getResumeStage(rlog)
  best_stage = rstage
  best_argv = rargv[:]
  if r0stage > rstage:
      best_stage = r0stage
      best_argv = r0argv[:]
  if best_stage == _stage_alldone:
     print >> sys.stderr, "Nothing to resume."
     sys.exit(1)

  global resumeStage
  resumeStage = best_stage
  return best_argv

def setRunStage(stnum):
   global currentStage
   print >> run_log, "#>"+stageNames[stnum]+":"
   currentStage = stnum

def init_logger(log_fname):
    global tophat_logger
    tophat_logger = logging.getLogger('project')
    formatter = logging.Formatter('%(asctime)s %(message)s', '[%Y-%m-%d %H:%M:%S]')
    tophat_logger.setLevel(logging.DEBUG)

    hstream = logging.StreamHandler(sys.stderr)
    hstream.setFormatter(formatter)
    tophat_logger.addHandler(hstream)
    #
    # Output logging information to file
    if os.path.isfile(log_fname):
        os.remove(log_fname)
    global tophat_log
    logfh = logging.FileHandler(log_fname)
    logfh.setFormatter(formatter)
    tophat_logger.addHandler(logfh)
    tophat_log=logfh.stream

# TopHatParams captures all of the runtime parameters used by TopHat, and many
# of these are passed as command line options to executables run by the pipeline

# This class and its nested classes also do options parsing through parse_options()
# and option validation via the member function check()

class BowtieFltFiles:
    def __init__(self,
          seqfiles=None, qualfiles=None,
          mappings=None,
          unmapped_reads=None,
          multihit_reads=None):
        self.seqfiles=seqfiles
        self.qualfiles=qualfiles
        self.mappings=mappings
        self.unmapped_reads=unmapped_reads
        self.multihit_reads=multihit_reads

class TopHatParams:

    # SpliceConstraints is a group of runtime parameters that specify what
    # constraints to put on junctions discovered by the program.  These constraints
    # are used to filter out spurious/false positive junctions.

    class SpliceConstraints:
        def __init__(self,
                     min_anchor_length,
                     min_intron_length,
                     max_intron_length,
                     splice_mismatches,
                     min_isoform_fraction):
            self.min_anchor_length = min_anchor_length
            self.min_intron_length = min_intron_length
            self.max_intron_length = max_intron_length
            self.splice_mismatches = splice_mismatches
            self.min_isoform_fraction = min_isoform_fraction

        def parse_options(self, opts):
            for option, value in opts:
                if option in ("-m", "--splice-mismatches"):
                    self.splice_mismatches = int(value)
                elif option in ("-a", "--min-anchor"):
                    self.min_anchor_length = int(value)
                elif option in ("-F", "--min-isoform-fraction"):
                    self.min_isoform_fraction = float(value)
                elif option in ("-i", "--min-intron-length"):
                    self.min_intron_length = int(value)
                elif option in ("-I", "--max-intron-length"):
                    self.max_intron_length = int(value)

        def check(self):
            if self.splice_mismatches not in [0,1,2]:
                die("Error: arg to --splice-mismatches must be 0, 1, or 2")
            if self.min_anchor_length < 4:
                die("Error: arg to --min-anchor-len must be greater than 4")
            if self.min_isoform_fraction < 0.0 or self.min_isoform_fraction > 1.0:
                die("Error: arg to --min-isoform-fraction must be between 0.0 and 1.0")
            if self.min_intron_length <= 0:
                die("Error: arg to --min-intron-length must be greater than 0")
            if self.max_intron_length <= 0:
                die("Error: arg to --max-intron-length must be greater than 0")

    # SystemParams is a group of runtime parameters that determine how to handle
    # temporary files produced during a run and how many threads to use for threaded
    # stages of the pipeline (e.g. Bowtie)

    class SystemParams:
        def __init__(self,
                     num_threads,
                     keep_tmp):
            self.num_threads = num_threads
            self.keep_tmp = keep_tmp
            self.zipper = "gzip"
            self.zipper_opts= []

        def parse_options(self, opts):
            global use_zpacker
            global use_BWT_FIFO
            for option, value in opts:
                if option in ("-p", "--num-threads"):
                    self.num_threads = int(value)
                elif option == "--keep-tmp":
                    self.keep_tmp = True
                elif option in ("-z","--zpacker"):
                    if value.lower() in ["-", " ", ".", "0", "none", "f", "false", "no"]:
                        value=""
                    self.zipper = value
                    #if not self.zipper:
                    #   self.zipper='gzip'
                elif option in ("-X", "--unmapped-fifo"):
                    use_BWT_FIFO=True
            if self.zipper:
                use_zpacker=True
                if self.num_threads>1 and not self.zipper_opts:
                    if self.zipper.endswith('pxz'):
                         self.zipper_opts.append('-T'+str(self.num_threads))
                    elif self.zipper.endswith('pbzip2') or self.zipper.endswith('pigz'):
                         self.zipper_opts.append('-p'+str(self.num_threads))
            else:
                use_zpacker=False
                if use_BWT_FIFO: use_BWT_FIFO=False
        def cmd(self):
            cmdline=[]
            if self.zipper:
                 cmdline.extend(['-z',self.zipper])
            if self.num_threads>1:
                 cmdline.extend(['-p'+str(self.num_threads)])
            return cmdline

        def check(self):
            if self.num_threads<1 :
                 die("Error: arg to --num-threads must be greater than 0")
            if self.zipper:
                xzip=which(self.zipper)
                if not xzip:
                    die("Error: cannot find compression program "+self.zipper)

    # ReadParams is a group of runtime parameters that specify various properties
    # of the user's reads (e.g. which quality scale their are on, how long the
    # fragments are, etc).
    class ReadParams:
        def __init__(self,
                     solexa_quals,
                     phred64_quals,
                     quals,
                     integer_quals,
                     color,
                     library_type,
                     seed_length,
                     # reads_format,
                     mate_inner_dist,
                     mate_inner_dist_std_dev,
                     read_group_id,
                     sample_id,
                     library_id,
                     description,
                     seq_platform_unit,
                     seq_center,
                     seq_run_date,
                     seq_platform):
            self.solexa_quals = solexa_quals
            self.phred64_quals = phred64_quals
            self.quals = quals
            self.integer_quals = integer_quals
            self.color = color
            self.library_type = library_type
            self.seed_length = seed_length
            # self.reads_format = reads_format
            self.mate_inner_dist = mate_inner_dist
            self.mate_inner_dist_std_dev = mate_inner_dist_std_dev
            self.read_group_id = read_group_id
            self.sample_id = sample_id
            self.library_id = library_id
            self.description = description
            self.seq_platform_unit = seq_platform_unit
            self.seq_center = seq_center
            self.seq_run_date = seq_run_date
            self.seq_platform = seq_platform

        def parse_options(self, opts):
            for option, value in opts:
                if option == "--solexa-quals":
                    self.solexa_quals = True
                elif option in ("--solexa1.3-quals", "--phred64-quals"):
                    self.phred64_quals = True
                elif option in ("-Q", "--quals"):
                    self.quals = True
                elif option == "--integer-quals":
                    self.integer_quals = True
                elif option in ("-C", "--color"):
                    self.color = True
                elif option == "--library-type":
                    self.library_type = value
                elif option in ("-s", "--seed-length"):
                    self.seed_length = int(value)
                elif option in ("-r", "--mate-inner-dist"):
                    self.mate_inner_dist = int(value)
                elif option == "--mate-std-dev":
                    self.mate_inner_dist_std_dev = int(value)
                elif option == "--rg-id":
                    self.read_group_id = value
                elif option == "--rg-sample":
                    self.sample_id = value
                elif option == "--rg-library":
                    self.library_id = value
                elif option == "--rg-description":
                    self.description = value
                elif option == "--rg-platform-unit":
                    self.seq_platform_unit = value
                elif option == "--rg-center":
                    self.seq_center = value
                elif option == "--rg-date":
                    self.seq_run_date = value
                elif option == "--rg-platform":
                    self.seq_platform = value

        def check(self):
            if self.seed_length and self.seed_length < 20:
                die("Error: arg to --seed-length must be at least 20")

            if self.mate_inner_dist_std_dev != None and self.mate_inner_dist_std_dev < 0:
                die("Error: arg to --mate-std-dev must at least 0")
            if (not self.read_group_id and self.sample_id) or (self.read_group_id and not self.sample_id):
                die("Error: --rg-id and --rg-sample must be specified or omitted together")

    # SearchParams is a group of runtime parameters that specify how TopHat will
    # search for splice junctions

    class SearchParams:
        def __init__(self,
                     min_closure_exon,
                     min_closure_intron,
                     max_closure_intron,
                     min_coverage_intron,
                     max_coverage_intron,
                     min_segment_intron,
                     max_segment_intron):

             self.min_closure_exon_length = min_closure_exon
             self.min_closure_intron_length = min_closure_intron
             self.max_closure_intron_length = max_closure_intron
             self.min_coverage_intron_length = min_coverage_intron
             self.max_coverage_intron_length = max_coverage_intron
             self.min_segment_intron_length = min_segment_intron
             self.max_segment_intron_length = max_segment_intron

        def parse_options(self, opts):
            for option, value in opts:
                if option == "--min-closure-exon":
                    self.min_closure_exon_length = int(value)
                if option == "--min-closure-intron":
                    self.min_closure_intron_length = int(value)
                if option == "--max-closure-intron":
                    self.max_closure_intron_length = int(value)
                if option == "--min-coverage-intron":
                    self.min_coverage_intron_length = int(value)
                if option == "--max-coverage-intron":
                    self.max_coverage_intron_length = int(value)
                if option == "--min-segment-intron":
                    self.min_segment_intron_length = int(value)
                if option == "--max-segment-intron":
                    self.max_segment_intron_length = int(value)

        def check(self):
            if self.min_closure_exon_length < 0:
                die("Error: arg to --min-closure-exon must be at least 20")
            if self.min_closure_intron_length < 0:
                die("Error: arg to --min-closure-intron must be at least 20")
            if self.max_closure_intron_length < 0:
                die("Error: arg to --max-closure-intron must be at least 20")
            if self.min_coverage_intron_length < 0:
                die("Error: arg to --min-coverage-intron must be at least 20")
            if self.max_coverage_intron_length < 0:
                die("Error: arg to --max-coverage-intron must be at least 20")
            if self.min_segment_intron_length < 0:
                die("Error: arg to --min-segment-intron must be at least 20")
            if self.max_segment_intron_length < 0:
                die("Error: arg to --max-segment-intron must be at least 20")

    class ReportParams:
        def __init__(self):
            self.sort_bam = True
            self.convert_bam = True

        def parse_options(self, opts):
            for option, value in opts:
                if option == "--no-sort-bam":
                    self.sort_bam = False
                if option == "--no-convert-bam":
                    self.convert_bam = False

    class Bowtie2Params:
        def __init__(self):
            self.very_fast = False
            self.fast = False
            self.sensitive = False
            self.very_sensitive = False

            self.N = 0
            self.L = 20
            self.i = "S,1,1.25"
            self.n_ceil = "L,0,0.15"
            self.gbar = 4

            self.mp = "6,2"
            self.np = 1
            self.rdg = "5,3"
            self.rfg = "5,3"
            # self.score_min = "L,-0.6,-0.6"
            self.score_min = None

            self.D = 15
            self.R = 2

        def parse_options(self, opts):
            for option, value in opts:
                if option == "--b2-very-fast":
                    self.very_fast = True
                if option == "--b2-fast":
                    self.fast = True
                if option == "--b2-sensitive":
                    self.sensitive = True
                if option == "--b2-very-sensitive":
                    self.very_sensitive = True

                if option == "--b2-N":
                    self.N = int(value)
                if option == "--b2-L":
                    self.L = 20
                if option == "--b2-i":
                    self.i = value
                if option == "--b2-n-ceil":
                    self.n_ceil = value
                if option == "--b2-gbar":
                    self.gbar = 4

                if option == "--b2-mp":
                    self.mp = value
                if option == "--b2-np":
                    self.np = int(value)
                if option == "--b2-rdg":
                    self.rdg = value
                if option == "--b2-rfg":
                    self.rfg = value
                if option == "--b2-score-min":
                    self.score_min = value

                if option == "--b2-D":
                    self.D = int(value)
                if option == "--b2-R":
                    self.R = int(value)

        def check(self):
            more_than_once = False
            if self.very_fast:
                if self.fast or self.sensitive or self.very_sensitive:
                    more_than_once = True
            else:
                if self.fast:
                    if self.sensitive or self.very_sensitive:
                        more_than_once = True
                else:
                    if self.sensitive and self.very_sensitive:
                        more_than_once = True

            if more_than_once:
                die("Error: use only one of --b2-very-fast, --b2-fast, --b2-sensitive, --b2-very-sensitive")

            if not self.N in [0, 1]:
                die("Error: arg to --b2-N must be either 0 or 1")

            function_re = r'^[CLSG],-?\d+(\.\d+)?,-?\d+(\.\d+)?$'
            function_match = re.search(function_re, self.i)

            if not function_match:
                die("Error: arg to --b2-i must be <func> (e.g. --b2-i S,1,1.25)")

            function_match = re.search(function_re, self.n_ceil)
            if not function_match:
                die("Error: arg to --b2-n-ceil must be <func> (e.g. --b2-n-ceil L,0,0.15)")

            if self.score_min:
                function_match = re.search(function_re, self.score_min)
                if not function_match:
                    die("Error: arg to --b2-score-min must be <func> (e.g. --b2-score-min L,-0.6,-0.6)")

            pair_re = r'^\d+,\d+$'
            pair_match = re.search(pair_re, self.mp)
            if not pair_match:
                die("Error: arg to --b2-mp must be <int>,<int> (e.g. --b2-mp 6,2)")

            pair_match = re.search(pair_re, self.rdg)
            if not pair_match:
                die("Error: arg to --b2-rdg must be <int>,<int> (e.g. --b2-mp 5,3)")

            pair_match = re.search(pair_re, self.rfg)
            if not pair_match:
                die("Error: arg to --b2-rfg must be <int>,<int> (e.g. --b2-mp 5,3)")


    def __init__(self):
        self.splice_constraints = self.SpliceConstraints(8,     # min_anchor
                                                         50,    # min_intron
                                                         500000, # max_intron
                                                         0,     # splice_mismatches
                                                         0.15)  # min_isoform_frac

        self.preflt_data = [ BowtieFltFiles(), BowtieFltFiles() ]
        self.sam_header = None
        self.read_params = self.ReadParams(False,               # solexa_scale
                                           False,
                                           False,               # quals
                                           None,                # integer quals
                                           False,               # SOLiD - color space
                                           "",                  # library type (e.g. "illumina-stranded-pair-end")
                                           None,                # seed_length
                                         # "fastq",             # quality_format
                                           None,                # mate inner distance
                                           20,                  # mate inner dist std dev
                                           None,                # read group id
                                           None,                # sample id
                                           None,                # library id
                                           None,                # description
                                           None,                # platform unit (i.e. lane)
                                           None,                # sequencing center
                                           None,                # run date
                                           None)                # sequencing platform

        self.system_params = self.SystemParams(1,               # bowtie_threads (num_threads)
                                               False)           # keep_tmp

        self.search_params = self.SearchParams(100,             # min_closure_exon_length
                                               50,              # min_closure_intron_length
                                               5000,            # max_closure_intron_length
                                               50,              # min_coverage_intron_length
                                               20000,           # max_coverage_intron_length
                                               50,              # min_segment_intron_length
                                               500000)          # max_segment_intron_length

        self.report_params = self.ReportParams()

        self.bowtie2_params = self.Bowtie2Params()

        self.bowtie2 = True
        self.gff_annotation = None
        self.transcriptome_only = False
        self.transcriptome_index = None
        self.transcriptome_outdir = None
        self.transcriptome_buildonly = None
        self.raw_junctions = None
        self.resume_dir = None
        self.find_novel_juncs = True
        self.find_novel_indels = True
        self.find_novel_fusions = True
        self.find_GFF_juncs = True
        self.max_hits = 20
        self.suppress_hits = False
        self.t_max_hits = 60
        self.max_seg_hits = 40
        self.prefilter_multi = False
        self.read_mismatches = 2
        self.read_gap_length = 2
        self.read_edit_dist = 2
        self.read_realign_edit_dist = None
        self.segment_length = 25
        self.segment_mismatches = 2
        self.bowtie_alignment_option = "-v"
        self.max_insertion_length = 3
        self.max_deletion_length = 3
        self.raw_insertions = None
        self.raw_deletions = None
        self.coverage_search = None
        self.closure_search = False
        #self.butterfly_search = None
        self.butterfly_search = False
        self.microexon_search = False
        self.report_secondary_alignments = False
        self.report_discordant_pair_alignments = True
        self.report_mixed_alignments = True

        # experimental -W option to activate score and edit distance filtering
        # in fix_map_ordering (hits post processing)
        self.b2scoreflt = False

        self.keep_fasta_order = False
        self.partial_mapping = False

        self.fusion_search = False
        self.fusion_anchor_length = 20
        self.fusion_min_dist = 10000000
        self.fusion_read_mismatches = 2
        self.fusion_multireads = 2
        self.fusion_multipairs = 2
        self.fusion_ignore_chromosomes = []
        self.fusion_do_not_resolve_conflicts = False

    def check(self):
        self.splice_constraints.check()
        self.read_params.check()
        self.system_params.check()
        if self.segment_length < 10:
            die("Error: arg to --segment-length must at least 10")
        if self.segment_mismatches < 0 or self.segment_mismatches > 3:
            die("Error: arg to --segment-mismatches must in [0, 3]")
        if self.read_params.color:
            if self.bowtie2:
                th_log("Warning: bowtie2 in colorspace is not supported; --bowtie1 option assumed.")
                self.bowtie2=False
            if self.fusion_search:
                die("Error: fusion-search in colorspace is not yet supported")
            if self.butterfly_search:
                die("Error: butterfly-search in colorspace is not yet supported")

        self.bowtie2_params.check()

        if self.bowtie2 and self.fusion_search:
            th_logp("\tWarning: --fusion-search with Bowtie2 may not work well as it may require much memory space and produce many spurious fusions.  Please try --bowtie1 option if this doesn't work.")

        library_types = ["fr-unstranded", "fr-firststrand", "fr-secondstrand"]

        if self.read_params.library_type and self.read_params.library_type not in library_types:
            die("Error: library-type should be one of: "+', '.join(library_types))

        self.search_params.max_closure_intron_length = min(self.splice_constraints.max_intron_length,
                                                           self.search_params.max_closure_intron_length)

        self.search_params.max_segment_intron_length = min(self.splice_constraints.max_intron_length,
                                                           self.search_params.max_segment_intron_length)

        self.search_params.max_coverage_intron_length = min(self.splice_constraints.max_intron_length,
                                                            self.search_params.max_coverage_intron_length)

        if self.max_insertion_length >= self.segment_length:
            die("Error: the max insertion length ("+self.max_insertion_length+") can not be equal to or greater than the segment length ("+self.segment_length+")")

        if self.max_insertion_length < 0:
            die("Error: the max insertion length ("+self.max_insertion_length+") can not be less than 0")

        if self.max_deletion_length >= self.splice_constraints.min_intron_length:
            die("Error: the max deletion length ("+self.max_deletion_length+") can not be equal to or greater than the min intron length ("+self.splice_constraints.min_intron_length+")")

        if self.max_deletion_length < 0:
           die("Error: the max deletion length ("+self.max_deletion_length+") can not be less than 0")

        if self.read_mismatches > self.read_edit_dist or self.read_gap_length > self.read_edit_dist:
            die("Error: the read mismatches (" + str(self.read_mismatches) + ") and the read gap length (" + str(self.read_edit_dist) + ") should be less than or equal to the read edit dist (" + str(self.read_edit_dist) + ")\n" + \
                "Either decrease --read-mismatches or --read-gap-length, or increase --read-edit-dist")


        self.search_params.min_segment_intron_length = min(self.search_params.min_segment_intron_length, self.splice_constraints.min_intron_length)
        self.search_params.max_segment_intron_length = max(self.search_params.max_segment_intron_length, self.splice_constraints.max_intron_length)


    def cmd(self):
        cmd = ["--min-anchor", str(self.splice_constraints.min_anchor_length),
               "--splice-mismatches", str(self.splice_constraints.splice_mismatches),
               "--min-report-intron", str(self.splice_constraints.min_intron_length),
               "--max-report-intron", str(self.splice_constraints.max_intron_length),
               "--min-isoform-fraction", str(self.splice_constraints.min_isoform_fraction),
               "--output-dir", output_dir,
               "--max-multihits", str(self.max_hits),
               "--max-seg-multihits", str(self.max_seg_hits),
               "--segment-length", str(self.segment_length),
               "--segment-mismatches", str(self.segment_mismatches),
               "--min-closure-exon", str(self.search_params.min_closure_exon_length),
               "--min-closure-intron", str(self.search_params.min_closure_intron_length),
               "--max-closure-intron", str(self.search_params.max_closure_intron_length),
               "--min-coverage-intron", str(self.search_params.min_coverage_intron_length),
               "--max-coverage-intron", str(self.search_params.max_coverage_intron_length),
               "--min-segment-intron", str(self.search_params.min_segment_intron_length),
               "--max-segment-intron", str(self.search_params.max_segment_intron_length),
               "--read-mismatches", str(self.read_mismatches),
               "--read-gap-length", str(self.read_gap_length),
               "--read-edit-dist", str(self.read_edit_dist),
               "--read-realign-edit-dist", str(self.read_realign_edit_dist),
               "--max-insertion-length", str(self.max_insertion_length),
               "--max-deletion-length", str(self.max_deletion_length)]

        if self.suppress_hits:
            cmd.extend(["--suppress-hits"])

        if not self.bowtie2:
            cmd.extend(["--bowtie1"])

        if self.fusion_search:
            cmd.extend(["--fusion-search",
                        "--fusion-anchor-length", str(self.fusion_anchor_length),
                        "--fusion-min-dist", str(self.fusion_min_dist),
                        "--fusion-read-mismatches", str(self.fusion_read_mismatches),
                        "--fusion-multireads", str(self.fusion_multireads),
                        "--fusion-multipairs", str(self.fusion_multipairs)])

            if self.fusion_ignore_chromosomes:
                cmd.extend(["--fusion-ignore-chromosomes", ",".join(self.fusion_ignore_chromosomes)])

            if self.fusion_do_not_resolve_conflicts:
                cmd.extend(["--fusion-do-not-resolve-conflicts"])

        cmd.extend(self.system_params.cmd())

        if self.read_params.mate_inner_dist != None:
            cmd.extend(["--inner-dist-mean", str(self.read_params.mate_inner_dist),
                        "--inner-dist-std-dev", str(self.read_params.mate_inner_dist_std_dev)])
        if self.gff_annotation != None:
            cmd.extend(["--gtf-annotations", str(self.gff_annotation)])
            if gtf_juncs:
               cmd.extend(["--gtf-juncs", gtf_juncs])
        if self.closure_search == False:
            cmd.append("--no-closure-search")
        if not self.coverage_search:
            cmd.append("--no-coverage-search")
        if not self.microexon_search:
            cmd.append("--no-microexon-search")
        if self.butterfly_search:
            cmd.append("--butterfly-search")
        if self.read_params.solexa_quals:
            cmd.append("--solexa-quals")
        if self.read_params.quals:
            cmd.append("--quals")
        if self.read_params.integer_quals:
            cmd.append("--integer-quals")
        if self.read_params.color:
            cmd.append("--color")
        if self.read_params.library_type:
            cmd.extend(["--library-type", self.read_params.library_type])
        if self.read_params.read_group_id:
            cmd.extend(["--rg-id", self.read_params.read_group_id])
        if self.read_params.phred64_quals:
            cmd.append("--phred64-quals")
        return cmd

    # This is the master options parsing routine, which calls parse_options for
    # the delegate classes (e.g. SpliceConstraints) that handle certain groups
    # of options.
    def parse_options(self, argv):
        try:
            opts, args = getopt.getopt(argv[1:], "hvp:m:n:N:F:a:i:I:G:Tr:o:j:Xz:s:g:x:R:MQCW",
                                        ["version",
                                         "help",
                                         "output-dir=",
                                         "bowtie1",
                                         "solexa-quals",
                                         "solexa1.3-quals",
                                         "phred64-quals",
                                         "quals",
                                         "integer-quals",
                                         "color",
                                         "library-type=",
                                         "num-threads=",
                                         "splice-mismatches=",
                                         "max-multihits=",
                                         "suppress-hits",
                                         "min-isoform-fraction=",
                                         "min-anchor-length=",
                                         "min-intron-length=",
                                         "max-intron-length=",
                                         "GTF=",
                                         "transcriptome-only",
                                         "transcriptome-max-hits=",
                                         "transcriptome-index=",
                                         "raw-juncs=",
                                         "no-novel-juncs",
                                         "allow-fusions",
                                         "fusion-search",
                                         "fusion-anchor-length=",
                                         "fusion-min-dist=",
                                         "fusion-read-mismatches=",
                                         "fusion-multireads=",
                                         "fusion-multipairs=",
                                         "fusion-ignore-chromosomes=",
                                         "fusion-do-not-resolve-conflicts",
                                         "no-novel-indels",
                                         "no-gtf-juncs",
                                         "mate-inner-dist=",
                                         "mate-std-dev=",
                                         "no-coverage-search",
                                         "coverage-search",
                                         "prefilter-multihits",
                                         "microexon-search",
                                         "min-coverage-intron=",
                                         "max-coverage-intron=",
                                         "min-segment-intron=",
                                         "max-segment-intron=",
                                         "resume=",
                                         "seed-length=",
                                         "read-mismatches=",
                                         "read-gap-length=",
                                         "read-edit-dist=",
                                         "read-realign-edit-dist=",
                                         "segment-length=",
                                         "segment-mismatches=",
                                         "bowtie-n",
                                         "keep-tmp",
                                         "rg-id=",
                                         "rg-sample=",
                                         "rg-library=",
                                         "rg-description=",
                                         "rg-platform-unit=",
                                         "rg-center=",
                                         "rg-date=",
                                         "rg-platform=",
                                         "tmp-dir=",
                                         "zpacker=",
                                         "unmapped-fifo",
                                         "max-insertion-length=",
                                         "max-deletion-length=",
                                         "insertions=",
                                         "deletions=",
                                         "no-sort-bam",
                                         "no-convert-bam",
                                         "report-secondary-alignments",
                                         "no-discordant",
                                         "no-mixed",
                                         "keep-fasta-order",
                                         "allow-partial-mapping",
                                         "b2-very-fast",
                                         "b2-fast",
                                         "b2-sensitive",
                                         "b2-very-sensitive",
                                         "b2-N=",
                                         "b2-L=",
                                         "b2-i=",
                                         "b2-n-ceil=",
                                         "b2-gbar=",
                                         "b2-ma=",
                                         "b2-mp=",
                                         "b2-np=",
                                         "b2-rdg=",
                                         "b2-rfg=",
                                         "b2-score-min=",
                                         "b2-D=",
                                         "b2-R="])
        except getopt.error, msg:
            raise Usage(msg)

        self.splice_constraints.parse_options(opts)
        self.system_params.parse_options(opts)
        self.read_params.parse_options(opts)
        self.search_params.parse_options(opts)
        self.report_params.parse_options(opts)
        self.bowtie2_params.parse_options(opts)
        global use_BWT_FIFO
        global use_BAM_Unmapped
        if not self.read_params.color:
           use_BWT_FIFO=False
           use_BAM_Unmapped=True
        global output_dir
        global logging_dir
        global tmp_dir

        custom_tmp_dir = None
        custom_out_dir = None
        # option processing
        for option, value in opts:
            if option in ("-v", "--version"):
                print "TopHat v%s" % (get_version())
                sys.exit(0)
            if option in ("-h", "--help"):
                raise Usage(use_message)
            if option == "--bowtie1":
                self.bowtie2 = False
            if option in ("-g", "--max-multihits"):
                self.max_hits = int(value)
                self.max_seg_hits = max(10, self.max_hits * 2)
            if option == "--suppress-hits":
                self.suppress_hits = True
            if option in ("-x", "--transcriptome-max-hits"):
                self.t_max_hits = int(value)
            if option in ("-G", "--GTF"):
                self.gff_annotation = value
            if option in ("-T", "--transcriptome-only"):
                self.transcriptome_only = True
            if option == "--transcriptome-index":
                self.transcriptome_index = value
            if option in("-M", "--prefilter-multihits"):
                self.prefilter_multi = True
            if option in ("-j", "--raw-juncs"):
                self.raw_junctions = value
            if option == "--no-novel-juncs":
                self.find_novel_juncs = False
            if option == "--no-novel-indels":
                self.find_novel_indels = False
            if option == "--fusion-search":
                self.fusion_search = True
            if option == "--fusion-anchor-length":
                self.fusion_anchor_length = int(value)
            if option == "--fusion-min-dist":
                self.fusion_min_dist = int(value)
            if option == "--fusion-read-mismatches":
                self.fusion_read_mismatches = int(value)
            if option == "--fusion-multireads":
                self.fusion_multireads = int(value)
            if option == "--fusion-multipairs":
                self.fusion_multipairs = int(value)
            if option == "--fusion-ignore-chromosomes":
                self.fusion_ignore_chromosomes = value.split(",")
            if option == "--fusion-do-not-resolve-conflicts":
                self.fusion_do_not_resolve_conflicts = True
            if option == "--no-gtf-juncs":
                self.find_GFF_juncs = False
            if option == "--no-coverage-search":
                self.coverage_search = False
            if option == "--coverage-search":
                self.coverage_search = True
            # -W option : score and edit distance filtering in fix_map_ordering
            # this is *soft* post-processing of bowtie2 results, should be
            # more effectively implemented by using bowtie2's score function
            if option == "-W":
                self.b2scoreflt = True
            self.closure_search = False
            #if option == "--no-closure-search":
            #    self.closure_search = False
            #if option == "--closure-search":
            #    self.closure_search = True
            if option == "--microexon-search":
                self.microexon_search = True

            self.butterfly_search = False
            #if option == "--butterfly-search":
            #    self.butterfly_search = True
            #if option == "--no-butterfly-search":
            #    self.butterfly_search = False
            if option in ("-N", "--read-mismatches"):
                self.read_mismatches = int(value)
            if option == "--read-gap-length":
                self.read_gap_length = int(value)
            if option == "--read-edit-dist":
                self.read_edit_dist = int(value)
            if option == "--read-realign-edit-dist":
                self.read_realign_edit_dist = int(value)
            if option == "--segment-length":
                self.segment_length = int(value)
            if option == "--segment-mismatches":
                self.segment_mismatches = int(value)
            if option == "--bowtie-n":
                self.bowtie_alignment_option = "-n"
            if option == "--max-insertion-length":
                self.max_insertion_length = int(value)
            if option == "--max-deletion-length":
                self.max_deletion_length = int(value)
            if option == "--insertions":
                self.raw_insertions = value
            if option == "--deletions":
                self.raw_deletions = value
            if option == "--report-secondary-alignments":
                self.report_secondary_alignments = True
            if option == "--no-discordant":
                self.report_discordant_pair_alignments = False
            if option == "--no-mixed":
                self.report_mixed_alignments = False
            if option == "--keep-fasta-order":
                self.keep_fasta_order = True
            if option == "--allow-partial-mapping":
                self.partial_mapping = True
            if option in ("-o", "--output-dir"):
                custom_out_dir = value + "/"
            if option in ("-R", "--resume"):
                self.resume_dir = value
            if option == "--tmp-dir":
                custom_tmp_dir = value + "/"

        if self.transcriptome_only:
           self.find_novel_juncs=False
           self.find_novel_indels=False
        if custom_out_dir:
            output_dir = custom_out_dir
            logging_dir = output_dir + "logs/"
            tmp_dir = output_dir + "tmp/"
            sam_header = tmp_dir + "stub_header.sam"
        if custom_tmp_dir:
            tmp_dir = custom_tmp_dir
            sam_header = tmp_dir + "stub_header.sam"
        if len(args) < 2 and not self.resume_dir:
            if len(args) == 1 and self.transcriptome_index and self.gff_annotation:
              self.transcriptome_buildonly = True
            else:
              raise Usage(use_message)

        if self.read_realign_edit_dist == None:
            self.read_realign_edit_dist = self.read_edit_dist + 1

        return args


def nonzeroFile(filepath):
  if os.path.exists(filepath):
     fpath, fname=os.path.split(filepath)
     fbase, fext =os.path.splitext(fname)
     if fext.lower() == ".bam":
         samtools_view_cmd = [samtools_path, "view", filepath]
         samtools_view = subprocess.Popen(samtools_view_cmd, stdout=subprocess.PIPE)
         head_cmd = ["head", "-1"]
         head = subprocess.Popen(head_cmd, stdin=samtools_view.stdout, stdout=subprocess.PIPE)

         samtools_view.stdout.close() # as per http://bugs.python.org/issue7678
         output = head.communicate()[0][:-1]

         if len(output) > 0:
             return True
     else:
        if os.path.getsize(filepath)>25:
          return True
  return False


# check if a file exists and has non-zero (or minimum) size
def fileExists(filepath, minfsize=2):
  if os.path.exists(filepath) and os.path.getsize(filepath)>=minfsize:
     return True
  else:
     return False

def removeFileWithIndex(filepath):
    if os.path.exists(filepath):
        os.remove(filepath)

        fileindexpath = filepath + ".index"
        if os.path.exists(fileindexpath):
            os.remove(fileindexpath)

def getFileDir(filepath):
   #if fullpath given, returns path including the ending /
   fpath, fname=os.path.split(filepath)
   if fpath: fpath+='/'
   return fpath

def getFileBaseName(filepath):
   fpath, fname=os.path.split(filepath)
   fbase, fext =os.path.splitext(fname)
   fx=fext.lower()
   if (fx in ['.fq','.txt','.seq','.bwtout'] or fx.find('.fa')==0) and len(fbase)>0:
      return fbase
   elif fx == '.z' or fx.find('.gz')==0 or fx.find('.bz')==0:
      fb, fext = os.path.splitext(fbase)
      fx=fext.lower()
      if (fx in ['.fq','.txt','.seq','.bwtout'] or fx.find('.fa')==0) and len(fb)>0:
         return fb
      else:
         return fbase
   else:
     if len(fbase)>0:
        return fbase
     else:
        return fname

# Returns the current time in a nice format
def right_now():
    curr_time = datetime.now()
    return curr_time.strftime("%c")

# The TopHat logging formatter
def th_log(out_str):
  if tophat_logger:
       tophat_logger.info(out_str)

def th_logp(out_str=""):
  print >> sys.stderr, out_str
  if tophat_log:
        print >> tophat_log, out_str

def die(msg=None):
  if msg is not None:
    th_logp(msg)
  sys.exit(1)

# Ensures that the output, logging, and temp directories are present. If not,
# they are created
def prepare_output_dir():

    #th_log("Preparing output location "+output_dir)
    if os.path.exists(output_dir):
        pass
    else:
        os.mkdir(output_dir)

    if os.path.exists(logging_dir):
        pass
    else:
        os.mkdir(logging_dir)

    if os.path.exists(tmp_dir):
        pass
    else:
        try:
          os.makedirs(tmp_dir)
        except OSError, o:
          die("\nError creating directory %s (%s)" % (tmp_dir, o))


# to be added as preexec_fn for every subprocess.Popen() call:
# see http://bugs.python.org/issue1652
def subprocess_setup():
 # Python installs a SIGPIPE handler by default, which causes
 # gzip or other de/compression pipes to complain about "stdout: Broken pipe"
   signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# Check that the Bowtie index specified by the user is present and all files
# are there.
def check_bowtie_index(idx_prefix, is_bowtie2, add="(genome)"):
    if currentStage >= resumeStage:
       th_log("Checking for Bowtie index files "+add+"..")
    idxext="ebwt"
    bowtie_ver=""
    if is_bowtie2:
        idxext="bt2"
        bowtie_ver="2 "

    idx_fwd_1 = idx_prefix + ".1."+idxext
    idx_fwd_2 = idx_prefix + ".2."+idxext
    idx_rev_1 = idx_prefix + ".rev.1."+idxext
    idx_rev_2 = idx_prefix + ".rev.2."+idxext

    #bwtbotherr = "Warning: we do not recommend to have both Bowtie1 and Bowtie2 indexes in the same directory \n the genome sequence (*.fa) may not be compatible with one of them"
    bwtbotherr = "\tFound both Bowtie1 and Bowtie2 indexes."
    if os.path.exists(idx_fwd_1) and \
       os.path.exists(idx_fwd_2) and \
       os.path.exists(idx_rev_1) and \
       os.path.exists(idx_rev_2):
        if os.path.exists(idx_prefix + ".1.ebwt") and os.path.exists(idx_prefix + ".1.bt2"):
            print >> sys.stderr, bwtbotherr
        return
    else:
        if is_bowtie2:
            idxext="bt2l"
            bowtie_ver="2 "
            idx_fwd_1 = idx_prefix + ".1."+idxext
            idx_fwd_2 = idx_prefix + ".2."+idxext
            idx_rev_1 = idx_prefix + ".rev.1."+idxext
            idx_rev_2 = idx_prefix + ".rev.2."+idxext
            if os.path.exists(idx_fwd_1) and \
               os.path.exists(idx_fwd_2) and \
               os.path.exists(idx_rev_1) and \
               os.path.exists(idx_rev_2):
                return
            
        bwtidxerr="Error: Could not find Bowtie "+bowtie_ver+"index files (" + idx_prefix + ".*."+idxext+")"

        if is_bowtie2:
            bwtidx_env = os.environ.get("BOWTIE2_INDEXES")
        else:
            bwtidx_env = os.environ.get("BOWTIE_INDEXES")

        if bwtidx_env == None:
            die(bwtidxerr)
        if os.path.exists(bwtidx_env+idx_fwd_1) and \
           os.path.exists(bwtidx_env+idx_fwd_2) and \
           os.path.exists(bwtidx_env+idx_rev_1) and \
           os.path.exists(bwtidx_env+idx_rev_2):
            if os.path.exists(bwtidx_env + idx_prefix + ".1.ebwt") and os.path.exists(bwtidx_env + idx_prefix + ".1.bt2"):
                print >> sys.stderr, bwtbotherr
            return
        else:
            die(bwtidxerr)

# Reconstructs the multifasta file from which the Bowtie index was created, if
# it's not already there.
def bowtie_idx_to_fa(idx_prefix, is_bowtie2):
    idx_name = idx_prefix.split('/')[-1]
    th_log("Reconstituting reference FASTA file from Bowtie index")

    try:
        tmp_fasta_file_name = tmp_dir + idx_name + ".fa"
        tmp_fasta_file = open(tmp_fasta_file_name, "w")

        inspect_log = open(logging_dir + "bowtie_inspect_recons.log", "w")

        if is_bowtie2:
            inspect_cmd = [prog_path("bowtie2-inspect")]
        else:
            inspect_cmd = [prog_path("bowtie-inspect")]

        inspect_cmd += [idx_prefix]

        th_logp("  Executing: " + " ".join(inspect_cmd) + " > " + tmp_fasta_file_name)
        ret = subprocess.call(inspect_cmd,
                              stdout=tmp_fasta_file,
                              stderr=inspect_log)
        # Bowtie reported an error
        if ret != 0:
           die(fail_str+"Error: bowtie-inspect returned an error\n"+log_tail(logging_dir + "bowtie_inspect_recons.log"))

    # Bowtie not found
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            die(fail_str+"Error: bowtie-inspect not found on this system.  Did you forget to include it in your PATH?")

    return tmp_fasta_file_name

# Checks whether the multifasta file for the genome is present alongside the
# Bowtie index files for it.
def check_fasta(idx_prefix, is_bowtie2):
    th_log("Checking for reference FASTA file")
    idx_fasta = idx_prefix + ".fa"
    if os.path.exists(idx_fasta):
        return idx_fasta
    else:
        if is_bowtie2:
            bowtie_idx_env_var = os.environ.get("BOWTIE2_INDEXES")
        else:
            bowtie_idx_env_var = os.environ.get("BOWTIE_INDEXES")
        if bowtie_idx_env_var:
            idx_fasta = bowtie_idx_env_var + idx_prefix + ".fa"
            if os.path.exists(idx_fasta):
                return idx_fasta

        th_logp("\tWarning: Could not find FASTA file " + idx_fasta)
        idx_fa = bowtie_idx_to_fa(idx_prefix, is_bowtie2)
        return idx_fa

# Check that both the Bowtie index and the genome's fasta file are present
def check_index(idx_prefix, is_bowtie2):
    check_bowtie_index(idx_prefix, is_bowtie2)
    ref_fasta_file = check_fasta(idx_prefix, is_bowtie2)

    return (ref_fasta_file, None)

# Retrive a tuple containing the system's version of Bowtie.  Parsed from
# `bowtie --version`
def get_bowtie_version():
    try:
        # Launch Bowtie to capture its version info
        proc = subprocess.Popen([bowtie_path, "--version"],
                          stdout=subprocess.PIPE)

        stdout_value = proc.communicate()[0]

        bowtie_version = None
        if not stdout_value: stdout_value=''
        bowtie_out = stdout_value.splitlines()[0]
        version_str=" version "
        ver_str_idx = bowtie_out.find(version_str)
        if ver_str_idx != -1:
            version_val = bowtie_out[(ver_str_idx + len(version_str)):]
            bvers=re.findall(r'\d+', version_val)
            bowtie_version = [int(x) for x in bvers]
        while len(bowtie_version)<4:
            bowtie_version.append(0)
        return bowtie_version
    except OSError, o:
       errmsg=fail_str+str(o)+"\n"
       if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
           errmsg+="Error: bowtie not found on this system"
       die(errmsg)

def get_index_sam_header(params, idx_prefix, name = ""):
    noSkip = currentStage >= resumeStage
    try:
        temp_sam_header_filename = tmp_dir + "temp.samheader.sam"
        temp_sam_header_file = None
        if noSkip:
          temp_sam_header_file = open(temp_sam_header_filename, "w")

        bowtie_header_cmd = [bowtie_path]

        read_params = params.read_params
        if not params.bowtie2:
            bowtie_header_cmd += ["--sam"]

        if read_params.color:
            bowtie_header_cmd.append('-C')

        if params.bowtie2:
            bowtie_header_cmd += ["-x"]

        bowtie_header_cmd.extend([idx_prefix, '/dev/null'])
        if noSkip:
           subprocess.call(bowtie_header_cmd,
                   stdout=temp_sam_header_file,
                   stderr=open('/dev/null'))

           temp_sam_header_file.close()
           temp_sam_header_file = open(temp_sam_header_filename, "r")

        bowtie_sam_header_filename = tmp_dir + idx_prefix.split('/')[-1]
        if name != "":
             bowtie_sam_header_filename += ("_" + name)
        bowtie_sam_header_filename += ".bwt.samheader.sam"
        if not noSkip:
           return bowtie_sam_header_filename
        bowtie_sam_header_file = open(bowtie_sam_header_filename, "w")

        preamble = []
        sq_dict_lines = []

        for line in temp_sam_header_file.readlines():
            line = line.strip()
            if line.find("@SQ") != -1:
                # Sequence dictionary record
                cols = line.split('\t')
                seq_name = None
                for col in cols:
                    fields = col.split(':')
                    #print fields
                    if len(fields) > 0 and fields[0] == "SN":
                        seq_name = fields[1]
                if seq_name == None:
                    die("Error: malformed sequence dictionary in sam header")
                sq_dict_lines.append([seq_name,line])
            elif line.find("CL"):
                continue
            else:
                preamble.append(line)

        print >> bowtie_sam_header_file, "@HD\tVN:1.0\tSO:coordinate"
        if read_params.read_group_id and read_params.sample_id:
            rg_str = "@RG\tID:%s\tSM:%s" % (read_params.read_group_id,
                                            read_params.sample_id)
            if read_params.library_id:
                rg_str += "\tLB:%s" % read_params.library_id
            if read_params.description:
                rg_str += "\tDS:%s" % read_params.description
            if read_params.seq_platform_unit:
                rg_str += "\tPU:%s" % read_params.seq_platform_unit
            if read_params.seq_center:
                rg_str += "\tCN:%s" % read_params.seq_center
            if read_params.mate_inner_dist:
                rg_str += "\tPI:%s" % read_params.mate_inner_dist
            if read_params.seq_run_date:
                rg_str += "\tDT:%s" % read_params.seq_run_date
            if read_params.seq_platform:
                rg_str += "\tPL:%s" % read_params.seq_platform

            print >> bowtie_sam_header_file, rg_str

        if not params.keep_fasta_order:
            sq_dict_lines.sort(lambda x,y: cmp(x[0],y[0]))

        for [name, line] in sq_dict_lines:
            print >> bowtie_sam_header_file, line
        print >> bowtie_sam_header_file, "@PG\tID:TopHat\tVN:%s\tCL:%s" % (get_version(), run_cmd)

        bowtie_sam_header_file.close()
        temp_sam_header_file.close()
        return bowtie_sam_header_filename

    except OSError, o:
       errmsg=fail_str+str(o)+"\n"
       if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
           errmsg+="Error: bowtie not found on this system"
       die(errmsg)

# Make sure Bowtie is installed and is recent enough to be useful
def check_bowtie(params):
    bowtie_req=""
    if params.bowtie2:
        bowtie_req="2"
    log_msg = "Checking for Bowtie"
    th_log(log_msg)

    bowtie_bin = "bowtie"+bowtie_req

    global bowtie_path
    bowtie_version = None
    bowtie_path=which(bowtie_bin)
    if bowtie_path:
      bowtie_version = get_bowtie_version()
    if params.bowtie2 and bowtie_version == None:
        th_logp("  Bowtie 2 not found, checking for older version..")
        #try to fallback on bowtie 1
        params.bowtie2=False
        bowtie_path=which('bowtie')
        if bowtie_path:
           bowtie_version=get_bowtie_version()
    if bowtie_version == None:
           die("Error: Bowtie not found on this system.")
    if params.bowtie2:
        if bowtie_version[1] < 1 and bowtie_version[2] < 5:
            die("Error: TopHat requires Bowtie 2.0.5 or later")
    else:
        if bowtie_version[0] < 1 and (bowtie_version[1] < 12 or bowtie_version[2] < 9):
            die("Error: TopHat requires Bowtie 0.12.9 or later")
    th_logp("\t\t  Bowtie version:\t %s" % ".".join([str(x) for x in bowtie_version]))


# Retrive a tuple containing the system's version of samtools.  Parsed from
# `samtools`
def get_samtools_version():
    try:
        # Launch Bowtie to capture its version info
        proc = subprocess.Popen(samtools_path, stderr=subprocess.PIPE)
        samtools_out = proc.communicate()[1]

        # Find the version identifier
        version_match = re.search(r'Version:\s+(\d+)\.(\d+).(\d+)([a-zA-Z]?)', samtools_out)
        samtools_version_arr = [int(version_match.group(x)) for x in [1,2,3]]
        if version_match.group(4):
            samtools_version_arr.append(version_match.group(4))
        else:
            samtools_version_arr.append(0)

        return version_match.group(), samtools_version_arr
    except OSError, o:
       errmsg=fail_str+str(o)+"\n"
       if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
           errmsg+="Error: samtools not found on this system"
       die(errmsg)

# Make sure the SAM tools are installed and are recent enough to be useful
def check_samtools():
    #th_log("Checking for Samtools")
    global samtools_path
    samtools_path=prog_path("samtools_0.1.18")
    #samtools_version_str, samtools_version_arr = get_samtools_version()
    #if samtools_version_str == None:
    if not samtools_path:
        die("Error: Required samtools version not found on this system")
    #elif  samtools_version_arr[1] < 1 or samtools_version_arr[2] < 7:
    #    die("Error: TopHat2 requires Samtools 0.1.19")
    #th_logp("\t\tSamtools version:\t %s" % ".".join([str(x) for x in samtools_version_arr]))



class FastxReader:
  def __init__(self, i_file, is_color=0, fname=''):
    self.bufline=None
    self.format=None
    self.ifile=i_file
    self.nextRecord=None
    self.eof=None
    self.fname=fname
    self.lastline=None
    self.numrecords=0
    self.isColor=0
    if is_color : self.isColor=1
    # determine file type
    #no records processed yet, skip custom header lines if any
    hlines=10 # allow maximum 10 header lines
    self.lastline=" "
    while hlines>0 and self.lastline[0] not in "@>" :
       self.lastline=self.ifile.readline()
       hlines-=1
    if self.lastline[0] == '@':
      self.format='fastq'
      self.nextRecord=self.nextFastq
    elif self.lastline[0] == '>':
      self.format='fasta'
      self.nextRecord=self.nextFasta
    else:
      die("Error: cannot determine record type in input file %s" % fname)
    self.bufline=self.lastline
    self.lastline=None

  def nextFastq(self):
    # returning tuple: (seqID, sequence_string, seq_len, qv_string)
    seqid,seqstr,qstr,seq_len='','','',0
    if self.eof: return (seqid, seqstr, seq_len, qstr)
    fline=self.getLine #shortcut to save a bit of time
    line=fline()

    if not line : return (seqid, seqstr, seq_len, qstr)
    while len(line.rstrip())==0: # skip empty lines
      line=fline()
      if not line : return (seqid, seqstr,seq_len, qstr)
    try:
      if line[0] != "@":
          raise ValueError("Records in Fastq files should start with '@' character")

      seqid = line[1:].rstrip()
      seqstr = fline().rstrip()

      #There may now be more sequence lines, or the "+" quality marker line:
      while True:
          line = fline()
          if not line:
             raise ValueError("Premature end of file (missing quality values for "+seqid+")")
          if line[0] == "+":
             # -- sequence string ended
             #qtitle = line[1:].rstrip()
             #if qtitle and qtitle != seqid:
             #   raise ValueError("Different read ID for sequence and quality (%s vs %s)" \
             #                    % (seqid, qtitle))
             break
          seqstr += line.rstrip() #removes trailing newlines
          #loop until + found
      seq_len = len(seqstr)
      #at least one line of quality data should follow
      qstrlen=0
      #now read next lines as quality values until seq_len is reached
      while True:
          line=fline()
          if not line : break #end of file
          qstr += line.rstrip()
          qstrlen=len(qstr)
          if qstrlen + self.isColor >= seq_len :
               break # qv string has reached the length of seq string
          #loop until qv has the same length as seq

      if self.isColor:
           # and qstrlen==seq_len :
           if qstrlen==seq_len:
             #qual string may have a dummy qv at the beginning, should be stripped
             qstr = qstr[1:]
             qstrlen -= 1
           if qstrlen!=seq_len-1:
             raise ValueError("Length mismatch between sequence and quality strings "+ \
                                "for %s (%i vs %i)." % (seqid, seq_len, qstrlen))
      else:
           if seq_len != qstrlen :
              raise ValueError("Length mismatch between sequence and quality strings "+ \
                                "for %s (%i vs %i)." % (seqid, seq_len, qstrlen))
    except ValueError, err:
        die("\nError encountered parsing file "+self.fname+":\n "+str(err))
    #return the record
    self.numrecords+=1
    ##--discard the primer base [NO]
    if self.isColor :
        seq_len-=1
        seqstr = seqstr[1:]
    return (seqid, seqstr, seq_len, qstr)

  def nextFasta(self):
    # returning tuple: (seqID, sequence_string, seq_len)
    seqid,seqstr,seq_len='','',0
    fline=self.getLine # shortcut to readline function of f
    line=fline() # this will use the buffer line if it's there
    if not line : return (seqid, seqstr, seq_len, None)
    while len(line.rstrip())==0: # skip empty lines
      line=fline()
      if not line : return (seqid, seqstr, seq_len, None)
    try:
       if line[0] != ">":
          raise ValueError("Records in Fasta files must start with '>' character")
       seqid = line[1:].split()[0]
       #more sequence lines, or the ">" quality marker line:
       while True:
          line = fline()
          if not line: break
          if line[0] == '>':
             #next sequence starts here
             self.ungetLine()
             break
          seqstr += line.rstrip()
          #loop until '>' found
       seq_len = len(seqstr)
       if seq_len < 3:
          raise ValueError("Read %s too short (%i)." \
                           % (seqid, seq_len))
    except ValueError, err:
        die("\nError encountered parsing fasta file "+self.fname+"\n "+str(err))
    #return the record and continue
    self.numrecords+=1
    if self.isColor : # -- discard primer base
        seq_len-=1
        seqstr=seqstr[1:]
    return (seqid, seqstr, seq_len, None)

  def getLine(self):
      if self.bufline: #return previously buffered line
         r=self.bufline
         self.bufline=None
         return r
      else: #read a new line from stream and return it
         if self.eof: return None
         self.lastline=self.ifile.readline()
         if not self.lastline:
            self.eof=1
            return None
         return self.lastline
  def ungetLine(self):
      if self.lastline is None:
         th_logp("Warning: FastxReader called ungetLine() with no prior line!")
      self.bufline=self.lastline
      self.lastline=None
#< class FastxReader

def fa_write(fhandle, seq_id, seq):
    """
    Write to a file in the FASTA format.

    Arguments:
    - `fhandle`: A file handle open for writing
    - `seq_id`: The sequence id string for this sequence
    - `seq`: An unformatted string of the sequence to write
    """
    line_len = 60
    fhandle.write(">" + seq_id + "\n")
    for i in xrange(len(seq) / line_len + 1):
        start = i * line_len
        #end = (i+1) * line_len if (i+1) * line_len < len(seq) else len(seq)
        if (i+1) * line_len < len(seq):
             end = (i+1) * line_len
        else:
             end = len(seq)
        fhandle.write( seq[ start:end ] + "\n")

class ZReader:
    def __init__(self, filename, params, guess=True):
        self.fname=filename
        self.file=None
        self.fsrc=None
        self.popen=None
        sys_params = params.system_params
        pipecmd=[]
        s=filename.lower()
        if s.endswith(".bam"):
           pipecmd=[prog_path("bam2fastx")]
           if params.read_params.color:
               pipecmd+=["--color"]
           pipecmd+=["--all", "-"]
        else:
          if guess:
             if s.endswith(".z") or s.endswith(".gz") or s.endswith(".gzip"):
                  pipecmd=['gzip']
             elif s.endswith(".xz"):
                  pipecmd=['xz']
             else:
                  if s.endswith(".bz2") or s.endswith(".bzip2") or s.endswith(".bzip"):
                       pipecmd=['bzip2']
             if len(pipecmd)>0 and which(pipecmd[0]) is None:
                 die("Error: cannot find %s to decompress input file %s " % (pipecmd, filename))
             if len(pipecmd)>0:
                if pipecmd[0]=='gzip' and sys_params.zipper.endswith('pigz'):
                   pipecmd[0]=sys_params.zipper
                   pipecmd.extend(sys_params.zipper_opts)
                elif pipecmd[0]=='xz' and sys_params.zipper.endswith('pxz'):
                   pipecmd[0]=sys_params.zipper
                   pipecmd.extend(sys_params.zipper_opts)
                elif pipecmd[0]=='bzip2' and sys_params.zipper.endswith('pbzip2'):
                   pipecmd[0]=sys_params.zipper
                   pipecmd.extend(sys_params.zipper_opts)
          else: #not guessing, but must still check if it's a compressed file
             if use_zpacker and filename.endswith(".z"):
                pipecmd=[sys_params.zipper]
                pipecmd.extend(sys_params.zipper_opts)

          if pipecmd:
             pipecmd+=['-cd']
        if pipecmd:
           try:
              self.fsrc=open(self.fname, 'rb')
              self.popen=subprocess.Popen(pipecmd,
                    preexec_fn=subprocess_setup,
                    stdin=self.fsrc,
                    stdout=subprocess.PIPE, stderr=tophat_log, close_fds=True)
           except Exception:
              die("Error: could not open pipe "+' '.join(pipecmd)+' < '+ self.fname)
           self.file=self.popen.stdout
        else:
           self.file=open(filename)
    def close(self):
       if self.fsrc: self.fsrc.close()
       self.file.close()
       if self.popen:
           self.popen.wait()
           self.popen=None

class ZWriter:
   def __init__(self, filename, sysparams):
      self.fname=filename
      if use_zpacker:
          pipecmd=[sysparams.zipper,"-cf", "-"]
          self.ftarget=open(filename, "wb")
          try:
             self.popen=subprocess.Popen(pipecmd,
                   preexec_fn=subprocess_setup,
                   stdin=subprocess.PIPE,
                   stderr=tophat_log, stdout=self.ftarget, close_fds=True)
          except Exception:
              die("Error: could not open writer pipe "+' '.join(pipecmd)+' < '+ self.fname)
          self.file=self.popen.stdin # client writes to this end of the pipe
      else: #no compression
          self.file=open(filename, "w")
          self.ftarget=None
          self.popen=None
   def close(self):
      self.file.close()
      if self.ftarget: self.ftarget.close()
      if self.popen:
          self.popen.wait() #! required to actually flush the pipes (eek!)
          self.popen=None

# check_reads_format() examines the first few records in the user files
# to determines the file format
def check_reads_format(params, reads_files):
    #seed_len = params.read_params.seed_length
    #fileformat = params.read_params.reads_format

    observed_formats = set([])
    # observed_scales = set([])
    min_seed_len = 99999
    max_seed_len = 0
    files = reads_files.split(',')

    for f_name in files:
        #try:
        zf = ZReader(f_name, params)
        #except IOError:
        #   die("Error: could not open file "+f_name)
        freader=FastxReader(zf.file, params.read_params.color, zf.fname)
        toread=4 #just sample the first 4 reads
        while toread>0:
            seqid, seqstr, seq_len, qstr = freader.nextRecord()
            if not seqid: break
            toread-=1
            if seq_len < 20:
                  th_logp("Warning: found a read < 20bp in "+f_name)
            else:
                min_seed_len = min(seq_len, min_seed_len)
                max_seed_len = max(seq_len, max_seed_len)
        zf.close()
        observed_formats.add(freader.format)
#     if len(observed_formats) > 1:
#         die("Error: TopHat requires all reads be either FASTQ or FASTA.  Mixing formats is not supported.")
    fileformat=list(observed_formats)[0]
#     #if seed_len != None:
#     #    seed_len = max(seed_len, max_seed_len)
#     #else:
#     #    seed_len = max_seed_len
#     #print >> sys.stderr, "\tmin read length: %dbp, max read length: %dbp" % (min_seed_len, max_seed_len)
#     th_logp("\tformat:\t\t %s" % fileformat)
#     if fileformat == "fastq":
#         quality_scale = "phred33 (default)"
#         if params.read_params.solexa_quals and not params.read_params.phred64_quals:
#             quality_scale = "solexa33 (reads generated with GA pipeline version < 1.3)"
#         elif params.read_params.phred64_quals:
#             quality_scale = "phred64 (reads generated with GA pipeline version >= 1.3)"
#         th_logp("\tquality scale:\t %s" % quality_scale)
#     elif fileformat == "fasta":
#         if params.read_params.color:
#             params.read_params.integer_quals = True
    if params.read_params.color and fileformat == "fasta":
         params.read_params.integer_quals = True

    #print seed_len, format, solexa_scale
    #NOTE: seed_len will be re-evaluated later by prep_reads
    return TopHatParams.ReadParams(params.read_params.solexa_quals,
                                   params.read_params.phred64_quals,
                                   params.read_params.quals,
                                   params.read_params.integer_quals,
                                   params.read_params.color,
                                   params.read_params.library_type,
                                   # seed_len,
                                   params.read_params.seed_length,
                                   # fileformat,
                                   params.read_params.mate_inner_dist,
                                   params.read_params.mate_inner_dist_std_dev,
                                   params.read_params.read_group_id,
                                   params.read_params.sample_id,
                                   params.read_params.library_id,
                                   params.read_params.description,
                                   params.read_params.seq_platform_unit,
                                   params.read_params.seq_center,
                                   params.read_params.seq_run_date,
                                   params.read_params.seq_platform)

def grep_file(logfile, regex="warning"):
   f=open(logfile, "r")
   r=[]
   for line in f:
      if re.match(regex, line, re.IGNORECASE):
         r += [line.rstrip()]
   return r

def log_tail(logfile, lines=1):
    f=open(logfile, "r")
    f.seek(0, 2)
    fbytes= f.tell()
    size=lines
    block=-1
    while size > 0 and fbytes+block*1024  > 0:
        if (fbytes+block*1024 > 0):
            ##Seek back once more, if possible
            f.seek( block*1024, 2 )
        else:
            #Seek to the beginning
            f.seek(0, 0)
        data= f.read( 1024 )
        linesFound= data.count('\n')
        size -= linesFound
        block -= 1
    if (fbytes + block*1024 > 0):
       f.seek(block*1024, 2)
    else:
       f.seek(0,0)
    #f.readline() # find a newline
    lastBlocks= list( f.readlines() )
    f.close()
    return "".join(lastBlocks[-lines:])

# Format a DateTime as a pretty string.
# FIXME: Currently doesn't support days!
def formatTD(td):
    days = td.days
    hours = td.seconds // 3600
    minutes = (td.seconds % 3600) // 60
    seconds = td.seconds % 60

    if days > 0:
        return '%d days %02d:%02d:%02d' % (days, hours, minutes, seconds)
    else:
        return '%02d:%02d:%02d' % (hours, minutes, seconds)

class PrepReadsInfo:
    def __init__(self, fname, out_fname):
           self.min_len  = [0, 0]
           self.max_len  = [0, 0]
           self.in_count = [0, 0]
           self.out_count= [0, 0]
           self.kept_reads = [None, None]
           try:
             f=open(fname,"r")
             self.min_len[0]=int(f.readline().split("=")[-1])
             self.max_len[0]=int(f.readline().split("=")[-1])
             self.in_count[0]=int(f.readline().split("=")[-1])
             self.out_count[0]=int(f.readline().split("=")[-1])
             if (self.out_count[0]==0) or (self.max_len[0]<16):
               raise Exception()
             line=f.readline()
             if line and line.find("=") > 0:
                self.min_len[1]=int(line.split("=")[-1])
                self.max_len[1]=int(f.readline().split("=")[-1])
                self.in_count[1]=int(f.readline().split("=")[-1])
                self.out_count[1]=int(f.readline().split("=")[-1])
                if (self.out_count[1]==0) or (self.max_len[1]<16):
                   raise Exception()
           except Exception:
             die(fail_str+"Error retrieving prep_reads info.")
           sides=["left", "right"]
           for ri in (0,1):
               if self.in_count[ri]==0: break
               trashed=self.in_count[ri]-self.out_count[ri]
               self.kept_reads[ri]=out_fname.replace("%side%", sides[ri])
               th_logp("\t%5s reads: min. length=%s, max. length=%s, %s kept reads (%s discarded)" %  (sides[ri], self.min_len[ri], self.max_len[ri], self.out_count[ri], trashed))

def prep_reads_cmd(params, l_reads_list, l_quals_list=None, r_reads_list=None, r_quals_list=None, out_file=None, aux_file=None,
                                 index_file=None, filter_reads=[], hits_to_filter=[]):
  #generate a prep_reads cmd arguments
  prep_cmd = [prog_path("prep_reads")]

  prep_cmd.extend(params.cmd())

#   if params.read_params.reads_format == "fastq":
#       prep_cmd += ["--fastq"]
#   elif params.read_params.reads_format == "fasta":
#       prep_cmd += ["--fasta"]
  if hits_to_filter:
    prep_cmd += ["--flt-hits=" + ",".join(hits_to_filter)]
  if aux_file:
    prep_cmd += ["--aux-outfile="+aux_file]
  if index_file:
      prep_cmd += ["--index-outfile="+index_file] # could be a template
  if filter_reads:
    prep_cmd += ["--flt-reads=" + ",".join(filter_reads)]
  if params.sam_header:
    prep_cmd += ["--sam-header="+params.sam_header]
  if out_file:
    prep_cmd += ["--outfile="+out_file] #could be a template
  prep_cmd.append(l_reads_list)
  if l_quals_list:
        prep_cmd.append(l_quals_list)
  if r_reads_list:
    prep_cmd.append(r_reads_list)
    if r_quals_list:
        prep_cmd.append(r_quals_list)

  return prep_cmd

# Calls the prep_reads executable, which prepares an internal read library.
# The read library features reads with monotonically increasing integer IDs.
# prep_reads also filters out very low complexy or garbage reads as well as
# polyA reads.
#--> returns a PrepReadsInfo structure
def prep_reads(params, l_reads_list, l_quals_list, r_reads_list, r_quals_list, prefilter_reads=[]):
    reads_suffix = ".bam"
    use_bam = True

    #if params.read_params.color:
    #   reads_suffix = ".fq"
    #   use_bam = False

    # for parallelization, we don't compress the read files
    do_use_zpacker = use_zpacker and not use_bam
    if do_use_zpacker and params.system_params.num_threads > 1:
        do_use_zpacker = False

    if do_use_zpacker: reads_suffix += ".z"

    out_suffix = "_kept_reads" + reads_suffix
    #kept_reads_filename = tmp_dir + output_name + reads_suffix

    for side in ("left", "right"):
       kept_reads_filename = tmp_dir + side + out_suffix
       if resumeStage<1 and os.path.exists(kept_reads_filename):
          os.remove(kept_reads_filename)
    out_tmpl="left"
    out_fname=None
    kept_reads = None #output file handle
    if r_reads_list:
        out_tmpl="%side%"
    info_file = output_dir+"prep_reads.info"
    if fileExists(info_file,10) and resumeStage>0 :
        return PrepReadsInfo(info_file, tmp_dir + out_tmpl + out_suffix)

    if use_bam:
       out_fname = tmp_dir + out_tmpl + out_suffix
    else:
      #assumed no right reads given here, only one side is being processed
      kept_reads = open(tmp_dir + out_tmpl + out_suffix, "wb")
    log_fname=logging_dir + "prep_reads.log"
    filter_log = open(log_fname,"w")

    index_file = out_fname + ".index"
    if do_use_zpacker: index_file=None

    prep_cmd=prep_reads_cmd(params, l_reads_list, l_quals_list, r_reads_list, r_quals_list,
                                       out_fname, info_file, index_file, prefilter_reads)
    shell_cmd = ' '.join(prep_cmd)
    #finally, add the compression pipe if needed
    zip_cmd=[]
    if do_use_zpacker:
       zip_cmd=[ params.system_params.zipper ]
       zip_cmd.extend(params.system_params.zipper_opts)
       zip_cmd.extend(['-c','-'])
       shell_cmd +=' | '+' '.join(zip_cmd)
    if not use_bam: shell_cmd += ' >' +kept_reads_filename
    retcode = None
    try:
        print >> run_log, shell_cmd
        if do_use_zpacker:
            filter_proc = subprocess.Popen(prep_cmd,
                                  stdout=subprocess.PIPE,
                                  stderr=filter_log)
            zip_proc=subprocess.Popen(zip_cmd,
                                  preexec_fn=subprocess_setup,
                                  stdin=filter_proc.stdout,
                                  stderr=tophat_log, stdout=kept_reads)
            filter_proc.stdout.close() #as per http://bugs.python.org/issue7678
            zip_proc.communicate()
            retcode=filter_proc.poll()
            if retcode==0:
              retcode=zip_proc.poll()
        else:
            if use_bam:
              retcode = subprocess.call(prep_cmd, stderr=filter_log)
            else:
              retcode = subprocess.call(prep_cmd,
                                 stdout=kept_reads, stderr=filter_log)
        if retcode:
            die(fail_str+"Error running 'prep_reads'\n"+log_tail(log_fname))

    except OSError, o:
        errmsg=fail_str+str(o)
        die(errmsg+"\n"+log_tail(log_fname))

    if kept_reads: kept_reads.close()
    warnings=grep_file(log_fname)
    if warnings:
       th_logp("\n"+"\n".join(warnings)+"\n")
    return PrepReadsInfo(info_file, tmp_dir + out_tmpl + out_suffix)

# Call bowtie
def bowtie(params,
           bwt_idx_prefix,
           sam_headers,
           reads_list,
           # reads_format,
           num_mismatches,
           gap_length,
           edit_dist,
           realign_edit_dist,
           mapped_reads,
           unmapped_reads,
           extra_output = "",
           mapping_type = _reads_vs_G,
           multihits_out = None): #only --prefilter-multihits should activate this parameter for the initial prefilter search
    start_time = datetime.now()
    bwt_idx_name = bwt_idx_prefix.split('/')[-1]
    reads_file=reads_list[0]
    readfile_basename=getFileBaseName(reads_file)

    g_mapping, t_mapping, seg_mapping = False, False, False
    sam_header_filename = None
    genome_sam_header_filename = None
    if mapping_type == _reads_vs_T:
        t_mapping = True
        sam_header_filename = sam_headers[0]
        genome_sam_header_filename = sam_headers[1]
    else:
      sam_header_filename = sam_headers
      if mapping_type >= _segs_vs_G:
        seg_mapping = True
      else:
        g_mapping = True

    bowtie_str = "Bowtie"
    if params.bowtie2:
        bowtie_str += "2"

    if seg_mapping:
        if not params.bowtie2:
            backup_bowtie_alignment_option = params.bowtie_alignment_option
            params.bowtie_alignment_option = "-v"

    resume_skip = resumeStage > currentStage
    unmapped_reads_out=None
    if unmapped_reads:
         unmapped_reads_out=unmapped_reads+".fq"
    mapped_reads += ".bam"
    if unmapped_reads:
            unmapped_reads_out = unmapped_reads + ".bam"
    use_FIFO = use_BWT_FIFO and use_zpacker and unmapped_reads and params.read_params.color
    if use_FIFO:
         unmapped_reads_out+=".z"
    if resume_skip:
         #skipping this step
         return (mapped_reads, unmapped_reads_out)

    bwt_logname=logging_dir + 'bowtie.'+readfile_basename+'.log'

    if t_mapping:
       th_log("Mapping %s to transcriptome %s with %s %s" % (readfile_basename,
                     bwt_idx_name, bowtie_str, extra_output))
    else:
       qryname = readfile_basename
       if len(reads_list) > 1:
           bnames=[]
           for fname in reads_list:
              bnames += [getFileBaseName(fname)]
           qryname = ",".join(bnames)
       th_log("Mapping %s to genome %s with %s %s" % (qryname,
                     bwt_idx_name, bowtie_str, extra_output))

    if use_FIFO:
         global unmapped_reads_fifo
         unmapped_reads_fifo=unmapped_reads+".fifo"
         if os.path.exists(unmapped_reads_fifo):
              os.remove(unmapped_reads_fifo)
         try:
              os.mkfifo(unmapped_reads_fifo)
         except OSError, o:
              die(fail_str+"Error at mkfifo("+unmapped_reads_fifo+'). '+str(o))

    # Launch Bowtie
    try:
        bowtie_cmd = [bowtie_path]
#         if reads_format == "fastq":
#             bowtie_cmd += ["-q"]
#         elif reads_format == "fasta":
#             bowtie_cmd += ["-f"]
        if params.read_params.color:
            bowtie_cmd += ["-C", "--col-keepends"]

        unzip_cmd=None
        bam_input=False
        if len(reads_list) > 0 and reads_list[0].endswith('.bam'):
           bam_input=True
           unzip_cmd=[ prog_path('bam2fastx'), "--all" ]
           if params.read_params.color:
               unzip_cmd.append("--color")
           #if reads_format:
           #   unzip_cmd.append("--" + reads_format)
           unzip_cmd+=[reads_list[0]]

        if use_zpacker and (unzip_cmd is None):
          unzip_cmd=[ params.system_params.zipper ]
          unzip_cmd.extend(params.system_params.zipper_opts)
          unzip_cmd+=['-cd']

        fifo_pid=None
        if use_FIFO:
             unm_zipcmd=[ params.system_params.zipper ]
             unm_zipcmd.extend(params.system_params.zipper_opts)
             unm_zipcmd+=['-c']
             print >> run_log, ' '.join(unm_zipcmd)+' < '+ unmapped_reads_fifo + ' > '+ unmapped_reads_out + ' & '
             fifo_pid=os.fork()
             if fifo_pid==0:
                 def on_sig_exit(sig, func=None):
                    os._exit(os.EX_OK)
                 signal.signal(signal.SIGTERM, on_sig_exit)
                 subprocess.call(unm_zipcmd,
                                 stdin=open(unmapped_reads_fifo, "r"),
                                 stderr=tophat_log,
                                 stdout=open(unmapped_reads_out, "wb"))
                 os._exit(os.EX_OK)

        fix_map_cmd = [prog_path('fix_map_ordering')]
        if params.read_params.color:
            fix_map_cmd += ["--color"]

        if params.bowtie2:
            #if t_mapping or g_mapping:
                max_penalty, min_penalty = params.bowtie2_params.mp.split(',')
                max_penalty, min_penalty = int(max_penalty), int(min_penalty)
                min_score = (max_penalty - 1) * realign_edit_dist
                fix_map_cmd += ["--bowtie2-min-score", str(min_score)]
            # testing score filtering
                if params.b2scoreflt:
                   fix_map_cmd +=["-W"+str(min_score+max_penalty)]
        fix_map_cmd += ["--read-mismatches", str(params.read_mismatches),
                        "--read-gap-length", str(params.read_gap_length),
                        "--read-edit-dist", str(params.read_edit_dist),
                        "--read-realign-edit-dist", str(params.read_realign_edit_dist)]

        #write BAM file
        out_bam = mapped_reads

        if not t_mapping:
           fix_map_cmd += ["--index-outfile", mapped_reads + ".index"]
        if not params.bowtie2:
           fix_map_cmd += ["--bowtie1"]
        if multihits_out != None:
           if params.bowtie2:
               fix_map_cmd += ["--aux-outfile", params.preflt_data[multihits_out].multihit_reads]
           fix_map_cmd += ["--max-multihits", str(params.max_hits)]
        if t_mapping:
           out_bam = "-" # we'll pipe into map2gtf
        fix_map_cmd += ["--sam-header", sam_header_filename, "-", out_bam]
        if unmapped_reads:
            fix_map_cmd += [unmapped_reads_out]
        if t_mapping:
            max_hits = params.t_max_hits
        elif seg_mapping:
            max_hits = params.max_seg_hits
        else:
            max_hits = params.max_hits

        if num_mismatches > 3:
           num_mismatches = 3

        if params.bowtie2:
            if seg_mapping or multihits_out != None:
                # since bowtie2 does not suppress reads that map to too many places,
                # we suppress those in segment_juncs and long_spanning_reads.
                bowtie_cmd += ["-k", str(max_hits + 1)]
            else:
                bowtie_cmd += ["-k", str(max_hits)]

            bowtie2_params = params.bowtie2_params
            if seg_mapping:
                # after intensive testing,
                # the following parameters seem to work faster than Bowtie1 and as sensitive as Bowtie1,
                # but room for further improvements remains.
                bowtie_cmd += ["-N", str(min(num_mismatches, 1))]
                bowtie_cmd += ["-L", str(min(params.segment_length, 20))]
                # bowtie_cmd += ["-i", "C,10000,0"] # allow only one seed
                # bowtie_cmd += ["-L", "14"]
            else:
                bowtie2_preset = ""
                if bowtie2_params.very_fast:
                    bowtie2_preset = "--very-fast"
                elif bowtie2_params.fast:
                    bowtie2_preset = "--fast"
                elif bowtie2_params.sensitive:
                    bowtie2_preset = "--sensitive"
                elif bowtie2_params.very_sensitive:
                    bowtie2_preset = "--very-sensitive"

                if bowtie2_preset != "":
                    bowtie_cmd += [bowtie2_preset]
                else:
                    bowtie_cmd += ["-D", str(bowtie2_params.D),
                                   "-R", str(bowtie2_params.R),
                                   "-N", str(bowtie2_params.N),
                                   "-L", str(bowtie2_params.L),
                                   "-i", bowtie2_params.i]

                score_min = bowtie2_params.score_min
                if not score_min:
                    max_penalty, min_penalty = bowtie2_params.mp.split(',')
                    score_min_value = int(max_penalty) * edit_dist + 2
                    score_min = "C,-%d,0" % score_min_value

                # "--n-ceil" is not correctly parsed in Bowtie2,
                # I  (daehwan) already talked to Ben who will fix the problem.
                bowtie_cmd += [# "--n-ceil", bowtie2_params.n_ceil,
                               "--gbar", str(bowtie2_params.gbar),
                               "--mp", bowtie2_params.mp,
                               "--np", str(bowtie2_params.np),
                               "--rdg", bowtie2_params.rdg,
                               "--rfg", bowtie2_params.rfg,
                               "--score-min", score_min]

        else:
            bowtie_cmd += [params.bowtie_alignment_option, str(num_mismatches),
                           "-k", str(max_hits),
                           "-m", str(max_hits),
                           "-S"]

        bowtie_cmd += ["-p", str(params.system_params.num_threads)]

        if params.bowtie2: #always use headerless SAM file
            bowtie_cmd += ["--sam-no-hd"]
        else:
            bowtie_cmd += ["--sam-nohead"]

        if not params.bowtie2:
            if multihits_out != None:
                bowtie_cmd += ["--max", params.preflt_data[multihits_out].multihit_reads]
            else:
                bowtie_cmd += ["--max", "/dev/null"]

        if params.bowtie2:
            bowtie_cmd += ["-x"]

        bowtie_cmd += [ bwt_idx_prefix ]
        bowtie_proc=None
        shellcmd=""
        unzip_proc=None

        if multihits_out != None:
           #special prefilter bowtie run: we use prep_reads on the fly
           #in order to get multi-mapped reads to exclude later
           prep_cmd = prep_reads_cmd(params, params.preflt_data[0].seqfiles, params.preflt_data[0].qualfiles,
                                      params.preflt_data[1].seqfiles, params.preflt_data[1].qualfiles)
           prep_cmd.insert(1,"--flt-side="+str(multihits_out))
           sides=["left", "right"]
           preplog_fname=logging_dir + "prep_reads.prefilter_%s.log" % sides[multihits_out]
           prepfilter_log = open(preplog_fname,"w")
           unzip_proc = subprocess.Popen(prep_cmd,
                                stdout=subprocess.PIPE,
                                stderr=prepfilter_log)
           shellcmd=' '.join(prep_cmd) + "|"
        else:
           z_input=use_zpacker and reads_file.endswith(".z")
           if z_input:
              unzip_proc = subprocess.Popen(unzip_cmd,
                                     stdin=open(reads_file, "rb"),
                                     stderr=tophat_log, stdout=subprocess.PIPE)
              shellcmd=' '.join(unzip_cmd) + "< " +reads_file +"|"
           else:
               #must be uncompressed fastq input (unmapped reads from a previous run)
               #or a BAM file with unmapped reads
               if bam_input:
                   unzip_proc = subprocess.Popen(unzip_cmd, stderr=tophat_log, stdout=subprocess.PIPE)
                   shellcmd=' '.join(unzip_cmd) + "|"
               else:
                   bowtie_cmd += [reads_file]
                   if not unzip_proc:
                        bowtie_proc = subprocess.Popen(bowtie_cmd,
                                     stdout=subprocess.PIPE,
                                     stderr=open(bwt_logname, "w"))
        if unzip_proc:
              #input is compressed OR prep_reads is used as a filter
              bowtie_cmd += ['-']
              bowtie_proc = subprocess.Popen(bowtie_cmd,
                                     stdin=unzip_proc.stdout,
                                     stdout=subprocess.PIPE,
                                     stderr=open(bwt_logname, "w"))
              unzip_proc.stdout.close() # see http://bugs.python.org/issue7678

        shellcmd += ' '.join(bowtie_cmd) + '|' + ' '.join(fix_map_cmd)
        pipeline_proc = None
        fix_order_proc = None
        #write BAM format directly
        if t_mapping:
            #pipe into map2gtf
            fix_order_proc = subprocess.Popen(fix_map_cmd,
                                          stdin=bowtie_proc.stdout,
                                          stdout=subprocess.PIPE,
                                          stderr=tophat_log)
            bowtie_proc.stdout.close()
            m2g_cmd = [prog_path("map2gtf")]
            m2g_cmd += ["--sam-header", genome_sam_header_filename]
            #m2g_cmd.append(params.gff_annotation)
            m2g_cmd.append(params.transcriptome_index+".fa.tlst")
            m2g_cmd.append("-") #incoming uncompressed BAM stream
            m2g_cmd.append(mapped_reads)
            m2g_log = logging_dir + "m2g_"+readfile_basename+".out"
            m2g_err = logging_dir + "m2g_"+readfile_basename+".err"
            shellcmd += ' | '+' '.join(m2g_cmd)+ ' > '+m2g_log
            pipeline_proc = subprocess.Popen(m2g_cmd,
                                              stdin=fix_order_proc.stdout,
                                              stdout=open(m2g_log, "w"),
                                              stderr=open(m2g_err, "w"))
            fix_order_proc.stdout.close()
        else:
            fix_order_proc = subprocess.Popen(fix_map_cmd,
                                          stdin=bowtie_proc.stdout,
                                          stderr=tophat_log)
            bowtie_proc.stdout.close()
            pipeline_proc = fix_order_proc

        print >> run_log, shellcmd
        retcode = None
        if pipeline_proc:
            pipeline_proc.communicate()
            retcode = pipeline_proc.returncode
            bowtie_proc.wait()
            r=bowtie_proc.returncode
            if r:
              die(fail_str+"Error running bowtie:\n"+log_tail(bwt_logname,100))
        if use_FIFO:
            if fifo_pid and not os.path.exists(unmapped_reads_out):
                try:
                  os.kill(fifo_pid, signal.SIGTERM)
                except:
                  pass
        if retcode:
            die(fail_str+"Error running:\n"+shellcmd)
    except OSError, o:
        die(fail_str+"Error: "+str(o))

    # Success
    #finish_time = datetime.now()
    #duration = finish_time - start_time
    #print >> sys.stderr, "\t\t\t[%s elapsed]" %  formatTD(duration)
    if use_FIFO:
        try:
          os.remove(unmapped_reads_fifo)
        except:
          pass
    if multihits_out != None and not os.path.exists(params.preflt_data[multihits_out].multihit_reads):
        open(params.preflt_data[multihits_out].multihit_reads, "w").close()

    if seg_mapping:
        if not params.bowtie2:
            params.bowtie_alignment_option = backup_bowtie_alignment_option

    return (mapped_reads, unmapped_reads_out)


# Retrieve a .juncs file from a GFF file by calling the gtf_juncs executable
def get_gtf_juncs(gff_annotation):
    th_log("Reading known junctions from GTF file")
    gtf_juncs_log = open(logging_dir + "gtf_juncs.log", "w")

    gff_prefix = gff_annotation.split('/')[-1].split('.')[0]

    gtf_juncs_out_name  = tmp_dir + gff_prefix + ".juncs"
    gtf_juncs_out = open(gtf_juncs_out_name, "w")

    gtf_juncs_cmd=[prog_path("gtf_juncs"), gff_annotation]
    try:
        print >> run_log, " ".join(gtf_juncs_cmd), " > "+gtf_juncs_out_name
        retcode = subprocess.call(gtf_juncs_cmd,
                                  stderr=gtf_juncs_log,
                                  stdout=gtf_juncs_out)
        # cvg_islands returned an error
        if retcode == 1:
            th_logp("\tWarning: TopHat did not find any junctions in GTF file")
            return (False, gtf_juncs_out_name)
        elif retcode != 0:
            die(fail_str+"Error: GTF junction extraction failed with err ="+str(retcode))

    # cvg_islands not found
    except OSError, o:
       errmsg=fail_str+str(o)+"\n"
       if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
           errmsg+="Error: gtf_juncs not found on this system"
       die(errmsg)
    return (True, gtf_juncs_out_name)

# Call bowtie-build on the FASTA file of sythetic splice junction sequences
def build_juncs_bwt_index(is_bowtie2, external_splice_prefix, color):
    th_log("Indexing splices")
    bowtie_build_log = open(logging_dir + "bowtie_build.log", "w")

    #user_splices_out_prefix  = output_dir + "user_splices_idx"

    if is_bowtie2:
        bowtie_build_cmd = [prog_path("bowtie2-build")]
    else:
        bowtie_build_cmd = [prog_path("bowtie-build")]

    if color:
        bowtie_build_cmd += ["-C"]

    bowtie_build_cmd += [external_splice_prefix + ".fa",
                         external_splice_prefix]
    try:
        print >> run_log, " ".join(bowtie_build_cmd)
        retcode = subprocess.call(bowtie_build_cmd,
                                 stdout=bowtie_build_log)

        if retcode != 0:
            die(fail_str+"Error: Splice sequence indexing failed with err ="+ str(retcode))
    except OSError, o:
        errmsg=fail_str+str(o)+"\n"
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            errmsg+="Error: bowtie-build not found on this system"
        die(errmsg)
    return external_splice_prefix

# Build a splice index from a .juncs file, suitable for use with specified read
# (or read segment) lengths
def build_juncs_index(is_bowtie2,
                      min_anchor_length,
                      max_seg_len,
                      juncs_prefix,
                      external_juncs,
                      external_insertions,
                      external_deletions,
                      external_fusions,
                      reference_fasta,
                      color):
    th_log("Retrieving sequences for splices")
    juncs_file_list = ",".join(external_juncs)
    insertions_file_list = ",".join(external_insertions)
    deletions_file_list = ",".join(external_deletions)
    fusions_file_list = ",".join(external_fusions)

    # do not use insertions and deletions in case of Bowtie2
    if is_bowtie2:
        insertions_file_list = "/dev/null"
        deletions_file_list = "/dev/null"

    juncs_db_log = open(logging_dir + "juncs_db.log", "w")

    external_splices_out_prefix  = tmp_dir + juncs_prefix
    external_splices_out_name = external_splices_out_prefix + ".fa"

    external_splices_out = open(external_splices_out_name, "w")
    # juncs_db_cmd = [bin_dir + "juncs_db",
    juncs_db_cmd = [prog_path("juncs_db"),
                    str(min_anchor_length),
                    str(max_seg_len),
                    juncs_file_list,
                    insertions_file_list,
                    deletions_file_list,
                    fusions_file_list,
                    reference_fasta]
    try:
        print >> run_log, " ".join(juncs_db_cmd) + " > " + external_splices_out_name
        retcode = subprocess.call(juncs_db_cmd,
                                 stderr=juncs_db_log,
                                 stdout=external_splices_out)

        if retcode != 0:
            die(fail_str+"Error: Splice sequence retrieval failed with err ="+str(retcode))
    # juncs_db not found
    except OSError, o:
       errmsg=fail_str+str(o)+"\n"
       if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
           errmsg+="Error: juncs_db not found on this system"
       die(errmsg)

    external_splices_out_prefix = build_juncs_bwt_index(is_bowtie2, external_splices_out_prefix, color)
    return external_splices_out_prefix

def build_idx_from_fa(is_bowtie2, fasta_fname, out_dir, color):
    """ Build a bowtie index from a FASTA file.

    Arguments:
    - `fasta_fname`: File path to FASTA file.
    - `out_dir`: Output directory to place index in. (includes os.sep)

    Returns:
    - The path to the Bowtie index.
    """
    bwt_idx_path = out_dir + os.path.basename(fasta_fname).replace(".fa", "")

    if is_bowtie2:
        bowtie_idx_cmd = [prog_path("bowtie2-build")]
    else:
        bowtie_idx_cmd = [prog_path("bowtie-build")]

    if color:
        bowtie_idx_cmd += ["-C"]

    bowtie_idx_cmd += [fasta_fname,
                       bwt_idx_path]
    try:
        th_log("Building Bowtie index from " + os.path.basename(fasta_fname))
        print >> run_log, " ".join(bowtie_idx_cmd)
        retcode = subprocess.call(bowtie_idx_cmd,
                                  stdout=open(os.devnull, "w"),
                                  stderr=open(os.devnull, "w"))
        if retcode != 0:
            die(fail_str + "Error: Couldn't build bowtie index with err = "
                + str(retcode))
    except OSError, o:
       errmsg=fail_str+str(o)+"\n"
       if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
           errmsg+="Error: bowtie-build not found on this system"
       die(errmsg)

    return bwt_idx_path

# Print out the sam header, embedding the user's specified library properties.
# FIXME: also needs SQ dictionary lines
def write_sam_header(read_params, sam_file):
    print >> sam_file, "@HD\tVN:1.0\tSO:coordinate"
    if read_params.read_group_id and read_params.sample_id:
        rg_str = "@RG\tID:%s\tSM:%s" % (read_params.read_group_id,
                                        read_params.sample_id)
        if read_params.library_id:
            rg_str += "\tLB:%s" % read_params.library_id
        if read_params.description:
            rg_str += "\tDS:%s" % read_params.description
        if read_params.seq_platform_unit:
            rg_str += "\tPU:%s" % read_params.seq_platform_unit
        if read_params.seq_center:
            rg_str += "\tCN:%s" % read_params.seq_center
        if read_params.mate_inner_dist:
            rg_str += "\tPI:%s" % read_params.mate_inner_dist
        if read_params.seq_run_date:
            rg_str += "\tDT:%s" % read_params.seq_run_date
        if read_params.seq_platform:
            rg_str += "\tPL:%s" % read_params.seq_platform

        print >> sam_file, rg_str
    print >> sam_file, "@PG\tID:TopHat\tVN:%s\tCL:%s" % (get_version(), run_cmd)

# Write final TopHat output, via tophat_reports and wiggles
def compile_reports(params, sam_header_filename, ref_fasta, mappings, readfiles, gff_annotation):
    th_log("Reporting output tracks")
    left_maps, right_maps = mappings
    left_reads, right_reads = readfiles
    # left_maps = [x for x in left_maps if (os.path.exists(x) and os.path.getsize(x) > 25)]
    left_maps = ','.join(left_maps)

    if len(right_maps) > 0:
        # right_maps = [x for x in right_maps if (os.path.exists(x) and os.path.getsize(x) > 25)]
        right_maps = ','.join(right_maps)

    log_fname = logging_dir + "reports.log"
    report_log = open(log_fname, "w")
    junctions = output_dir + "junctions.bed"
    insertions = output_dir + "insertions.bed"
    deletions = output_dir + "deletions.bed"
    accepted_hits = output_dir + "accepted_hits"
    report_cmdpath = prog_path("tophat_reports")
    fusions = output_dir + "fusions.out"
    report_cmd = [report_cmdpath]

    alignments_output_filename = tmp_dir + "accepted_hits"

    report_cmd.extend(params.cmd())
    report_cmd += ["--sam-header", sam_header_filename]
    if params.report_secondary_alignments:
        report_cmd += ["--report-secondary-alignments"]

    if params.report_discordant_pair_alignments:
        report_cmd += ["--report-discordant-pair-alignments"]

    if params.report_mixed_alignments:
        report_cmd += ["--report-mixed-alignments"]

    report_cmd.extend(["--samtools="+samtools_path])

    b2_params = params.bowtie2_params
    max_penalty, min_penalty = b2_params.mp.split(',')
    report_cmd += ["--bowtie2-max-penalty", max_penalty,
                  "--bowtie2-min-penalty", min_penalty]

    report_cmd += ["--bowtie2-penalty-for-N", str(b2_params.np)]

    read_gap_open, read_gap_cont = b2_params.rdg.split(',')
    report_cmd += ["--bowtie2-read-gap-open", read_gap_open,
                  "--bowtie2-read-gap-cont", read_gap_cont]

    ref_gap_open, ref_gap_cont = b2_params.rfg.split(',')
    report_cmd += ["--bowtie2-ref-gap-open", ref_gap_open,
                  "--bowtie2-ref-gap-cont", ref_gap_cont]

    report_cmd.extend([ref_fasta,
                       junctions,
                       insertions,
                       deletions,
                       fusions,
                       alignments_output_filename,
                       left_maps,
                       left_reads])

    if len(right_maps) > 0 and right_reads:
        report_cmd.append(right_maps)
        report_cmd.append(right_reads)

    try:
        print >> run_log, " ".join(report_cmd)
        report_proc=subprocess.call(report_cmd,
                                            preexec_fn=subprocess_setup,
                                            stderr=report_log)
        if report_proc != 0:
              die(fail_str+"Error running "+" ".join(report_cmd)+"\n"+log_tail(log_fname))
        bam_parts = []
        for i in range(params.system_params.num_threads):
               bam_part_filename = "%s%d.bam" % (alignments_output_filename, i)
               if os.path.exists(bam_part_filename):
                  bam_parts.append(bam_part_filename)
               else:
                  break
        num_bam_parts = len(bam_parts)

        if params.report_params.sort_bam:
            pids = [0 for i in range(num_bam_parts)]
            sorted_bam_parts = ["%s%d_sorted" % (alignments_output_filename, i) for i in range(num_bam_parts)]
            #left_um_parts = ["%s%s%d_sorted" % (alignments_output_filename, i) for i in range(num_bam_parts)]
            #right_um_parts = ["%s%d_sorted" % (alignments_output_filename, i) for i in range(num_bam_parts)]
            for i in range(num_bam_parts):
                    bamsort_cmd = [samtools_path,
                                   "sort",
                                   bam_parts[i],
                                   sorted_bam_parts[i]]

                    sorted_bam_parts[i] += ".bam"
                    print >> run_log, " ".join(bamsort_cmd)

                    if i + 1 < num_bam_parts:
                        pid = os.fork()
                        if pid == 0:
                            subprocess.call(bamsort_cmd,
                                            stderr=open(logging_dir + "reports.samtools_sort.log%d" % i, "w"))
                            os._exit(os.EX_OK)
                        else:
                            pids[i] = pid
                    else:
                        subprocess.call(bamsort_cmd,
                                        stderr=open(logging_dir + "reports.samtools_sort.log%d" % i, "w"))

            for i in range(len(pids)):
                    if pids[i] > 0:
                        result = os.waitpid(pids[i], 0)
                        pids[i] = 0

            for bam_part in bam_parts:
                os.remove(bam_part)
            bam_parts = sorted_bam_parts[:]
        #-- endif sort_bam

        if num_bam_parts > 1:
            if params.report_params.sort_bam:
               bammerge_cmd = [samtools_path,
                    "merge","-f","-h", sam_header_filename]
               if not params.report_params.convert_bam:
                    bammerge_cmd += ["-u"]
            else: #not sorted, so just raw merge
               bammerge_cmd = [prog_path("bam_merge"), "-Q",
                     "--sam-header", sam_header_filename]

            if params.report_params.convert_bam:
               bammerge_cmd += ["%s.bam" % accepted_hits]
               bammerge_cmd += bam_parts
               print >> run_log, " ".join(bammerge_cmd)
               subprocess.call(bammerge_cmd,
                      stderr=open(logging_dir + "reports.merge_bam.log", "w"))
            else: #make .sam
               bammerge_cmd += ["-"]
               bammerge_cmd += bam_parts
               merge_proc = subprocess.Popen(bammerge_cmd,
                            stdout=subprocess.PIPE,
                            stderr=open(logging_dir + "reports.merge_bam.log", "w"))
               bam2sam_cmd = [samtools_path, "view", "-h", "-"]
               sam_proc = subprocess.Popen(bam2sam_cmd,
                              stdin=merge_proc.stdout,
                              stdout=open(accepted_hits + ".sam", "w"),
                              stderr=open(logging_dir + "accepted_hits_bam_to_sam.log", "w"))
               merge_proc.stdout.close()
               shellcmd = " ".join(bammerge_cmd) + " | " + " ".join(bam2sam_cmd)
               print >> run_log, shellcmd
               sam_proc.communicate()
               retcode = sam_proc.returncode
               if retcode:
                 die(fail_str+"Error running:\n"+shellcmd)
            for bam_part in bam_parts:
                os.remove(bam_part)
        else: # only one file
            move(bam_parts[0], accepted_hits+".bam")
            if not params.report_params.convert_bam:
               #just convert to .sam
               bam2sam_cmd = [samtools_path, "view", "-h", accepted_hits+".bam"]
               shellcmd = " ".join(bam2sam_cmd) + " > " + accepted_hits + ".sam"
               print >> run_log, shellcmd
               r = subprocess.call(bam2sam_cmd,
                              stdout=open(accepted_hits + ".sam", "w"),
                              stderr=open(logging_dir + "accepted_hits_bam_to_sam.log", "w"))
               if r != 0:
                  die(fail_str+"Error running: "+shellcmd)
               os.remove(accepted_hits+".bam")

    except OSError, o:
          die(fail_str+"Error: "+str(o)+"\n"+log_tail(log_fname))

    try:
    # -- merge the unmapped files
      um_parts = []
      um_merged = output_dir + "unmapped.bam"
      for i in range(params.system_params.num_threads):
          left_um_file =  tmp_dir + "unmapped_left_%d.bam" % i
          right_um_file = tmp_dir + "unmapped_right_%d.bam" % i
          um_len = len(um_parts)
          if nonzeroFile(left_um_file):
             um_parts.append(left_um_file)
          if right_reads and nonzeroFile(right_um_file):
             um_parts.append(right_um_file)

      if len(um_parts) > 0:
          if len(um_parts)==1:
            move(um_parts[0], um_merged)
          else:
            merge_cmd=[prog_path("bam_merge"), "-Q",
              "--sam-header", sam_header_filename, um_merged]
            merge_cmd += um_parts
            print >> run_log, " ".join(merge_cmd)
            ret = subprocess.call( merge_cmd,
                                   stderr=open(logging_dir + "bam_merge_um.log", "w") )
            if ret != 0:
                die(fail_str+"Error executing: "+" ".join(merge_cmd)+"\n"+log_tail(logging_dir+"bam_merge_um.log"))
            for um_part in um_parts:
                os.remove(um_part)

    except OSError, o:
          die(fail_str+"Error: "+str(o)+"\n"+log_tail(log_fname))

    return junctions


# Split up each read in a FASTQ file into multiple segments. Creates a FASTQ file
# for each segment  This function needs to be fixed to support mixed read length
# inputs
def open_output_files(prefix, num_files_prev, num_files, out_segf, extension, params):
       i = num_files_prev + 1
       while i <= num_files:
          segfname=prefix+("_seg%d" % i)+extension
          out_segf.append(ZWriter(segfname,params.system_params))
          i += 1

def split_reads(reads_filename,
                prefix,
                fasta,
                params,
                segment_length):
    #reads_file = open(reads_filename)
    out_segfiles = []
    if fasta:
        extension = ".fa"
    else:
        extension = ".fq"
    if use_zpacker: extension += ".z"
    existing_seg_files = glob.glob(prefix+"_seg*"+extension)
    if resumeStage > currentStage and len(existing_seg_files)>0:
         #skip this, we are going to return the existing files
         return existing_seg_files
    zreads = ZReader(reads_filename, params, False)

    def convert_color_to_bp(color_seq):
        decode_dic = { 'A0':'A', 'A1':'C', 'A2':'G', 'A3':'T', 'A4':'N', 'A.':'N', 'AN':'N',
                       'C0':'C', 'C1':'A', 'C2':'T', 'C3':'G', 'C4':'N', 'C.':'N', 'CN':'N',
                       'G0':'G', 'G1':'T', 'G2':'A', 'G3':'C', 'G4':'N', 'G.':'N', 'GN':'N',
                       'T0':'T', 'T1':'G', 'T2':'C', 'T3':'A', 'T4':'N', 'T.':'N', 'TN':'N',
                       'N0':'N', 'N1':'N', 'N2':'N', 'N3':'N', 'N4':'N', 'N.':'N', 'NN':'N',
                       '.0':'N', '.1':'N', '.2':'N', '.3':'N', '.4':'N', '..':'N', '.N':'N' }

        base = color_seq[0]
        bp_seq = base
        for ch in color_seq[1:]:
            base = decode_dic[base+ch]
            bp_seq += base
        return bp_seq

    def convert_bp_to_color(bp_seq):
        encode_dic = { 'AA':'0', 'CC':'0', 'GG':'0', 'TT':'0',
                       'AC':'1', 'CA':'1', 'GT':'1', 'TG':'1',
                       'AG':'2', 'CT':'2', 'GA':'2', 'TC':'2',
                       'AT':'3', 'CG':'3', 'GC':'3', 'TA':'3',
                       'A.':'4', 'C.':'4', 'G.':'4', 'T.':'4',
                       '.A':'4', '.C':'4', '.G':'4', '.T':'4',
                       '.N':'4', 'AN':'4', 'CN':'4', 'GN':'4',
                       'TN':'4', 'NA':'4', 'NC':'4', 'NG':'4',
                       'NT':'4', 'NN':'4', 'N.':'4', '..':'4' }

        base = bp_seq[0]
        color_seq = base
        for ch in bp_seq[1:]:
            color_seq += encode_dic[base + ch]
            base = ch

        return color_seq

    def split_record(read_name, read_seq, read_qual, out_segf, offsets, color):
        if color:
            color_offset = 1
            read_seq_temp = convert_color_to_bp(read_seq)

            seg_num = 1
            while seg_num + 1 < len(offsets):
                if read_seq[offsets[seg_num]+1] not in ['0', '1', '2', '3']:
                    return
                seg_num += 1
        else:
            color_offset = 0

        seg_num = 0
        last_seq_offset = 0
        while seg_num + 1 < len(offsets):
            f = out_segf[seg_num].file
            seg_seq = read_seq[last_seq_offset+color_offset:offsets[seg_num + 1]+color_offset]
            print >> f, "%s|%d:%d:%d" % (read_name,last_seq_offset,seg_num, len(offsets) - 1)
            if color:
                print >> f, "%s%s" % (read_seq_temp[last_seq_offset], seg_seq)
            else:
                print >> f, seg_seq
            if not fasta:
                seg_qual = read_qual[last_seq_offset:offsets[seg_num + 1]]
                print >> f, "+"
                print >> f, seg_qual
            seg_num += 1
            last_seq_offset = offsets[seg_num]

    line_state = 0
    read_name = ""
    read_seq = ""
    read_quals = ""
    num_segments = 0
    offsets = []
    for line in zreads.file:
        if line.strip() == "":
            continue
        if line_state == 0:
            read_name = line.strip()
        elif line_state == 1:
            read_seq = line.strip()

            read_length = len(read_seq)
            tmp_num_segments = read_length / segment_length
            offsets = [segment_length * i for i in range(0, tmp_num_segments + 1)]

            # Bowtie's minimum read length here is 20bp, so if the last segment
            # is between 20 and segment_length bp long, go ahead and write it out
            if read_length % segment_length >= min(segment_length - 2, 20):
                offsets.append(read_length)
                tmp_num_segments += 1
            else:
                offsets[-1] = read_length

            if tmp_num_segments == 1:
                offsets = [0, read_length]

            if tmp_num_segments > num_segments:
                open_output_files(prefix, num_segments, tmp_num_segments, out_segfiles, extension, params)
                num_segments = tmp_num_segments

            if fasta:
                split_record(read_name, read_seq, None, out_segfiles, offsets, params.read_params.color)
        elif line_state == 2:
            line = line.strip()
        else:
            read_quals = line.strip()
            if not fasta:
                split_record(read_name, read_seq, read_quals, out_segfiles, offsets, params.read_params.color)

        line_state += 1
        if fasta:
            line_state %= 2
        else:
            line_state %= 4
    zreads.close()
    out_fnames=[]
    for zf in out_segfiles:
        zf.close()
        out_fnames.append(zf.fname)
    #return [o.fname for o in out_segfiles]
    return out_fnames

# Find possible splice junctions using the "closure search" strategy, and report
# them in closures.juncs.  Calls the executable closure_juncs
def junctions_from_closures(params,
                            sam_header_filename,
                            left_maps,
                            right_maps,
                            ref_fasta):
    th_log("Searching for junctions via mate-pair closures")


    #maps = [x for x in seg_maps if (os.path.exists(x) and os.path.getsize(x) > 0)]
    #if len(maps) == 0:
    #    return None
    slash = left_maps[0].rfind('/')
    juncs_out = ""
    if slash != -1:
        juncs_out += left_maps[0][:slash+1]
    fusions_out = juncs_out

    juncs_out += "closure.juncs"
    fusions_out += "closure.fusions"

    juncs_log = open(logging_dir + "closure.log", "w")
    juncs_cmdpath=prog_path("closure_juncs")
    juncs_cmd = [juncs_cmdpath]

    left_maps = ','.join(left_maps)
    right_maps = ','.join(right_maps)

    juncs_cmd.extend(params.cmd())
    juncs_cmd.extend(["--sam-header", sam_header_filename,
                      juncs_out,
                      fusions_out,
                      ref_fasta,
                      left_maps,
                      right_maps])
    try:
        print >> run_log, ' '.join(juncs_cmd)
        retcode = subprocess.call(juncs_cmd,
                                 stderr=juncs_log)

        # spanning_reads returned an error
        if retcode != 0:
           die(fail_str+"Error: closure-based junction search failed with err ="+str(retcode))
    # cvg_islands not found
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
           th_logp(fail_str + "Error: closure_juncs not found on this system")
        die(str(o))
    return [juncs_out]

# Find possible junctions by examining coverage and split segments in the initial
# map and segment maps.  Report junctions, insertions, and deletions in segment.juncs,
# segment.insertions, and segment.deletions.  Calls the executable
# segment_juncs
def junctions_from_segments(params,
                            sam_header_filename,
                            left_reads,
                            left_reads_map,
                            left_seg_maps,
                            right_reads,
                            right_reads_map,
                            right_seg_maps,
                            unmapped_reads,
                            ref_fasta):
    # if left_reads_map != left_seg_maps[0]:

    out_path=getFileDir(left_seg_maps[0])
    juncs_out=out_path+"segment.juncs"
    insertions_out=out_path+"segment.insertions"
    deletions_out =out_path+"segment.deletions"
    fusions_out = out_path+"segment.fusions"
    if resumeStage>currentStage and fileExists(juncs_out):
       return [juncs_out, insertions_out, deletions_out, fusions_out]
    th_log("Searching for junctions via segment mapping")
    if params.coverage_search == True:
        print >> sys.stderr, "\tCoverage-search algorithm is turned on, making this step very slow"
        print >> sys.stderr, "\tPlease try running TopHat again with the option (--no-coverage-search) if this step takes too much time or memory."

    left_maps = ','.join(left_seg_maps)
    log_fname = logging_dir + "segment_juncs.log"
    segj_log = open(log_fname, "w")
    segj_cmd = [prog_path("segment_juncs")]

    segj_cmd.extend(params.cmd())
    segj_cmd.extend(["--sam-header", sam_header_filename,
                     "--ium-reads", ",".join(unmapped_reads),
                     ref_fasta,
                     juncs_out,
                     insertions_out,
                     deletions_out,
                     fusions_out,
                     left_reads,
                     left_reads_map,
                     left_maps])
    if right_seg_maps:
        right_maps = ','.join(right_seg_maps)
        segj_cmd.extend([right_reads, right_reads_map, right_maps])
    try:
        print >> run_log, " ".join(segj_cmd)
        retcode = subprocess.call(segj_cmd,
                                 preexec_fn=subprocess_setup,
                                 stderr=segj_log)

        # spanning_reads returned an error
        if retcode != 0:
           die(fail_str+"Error: segment-based junction search failed with err ="+str(retcode)+"\n"+log_tail(log_fname))

    # cvg_islands not found
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
           th_logp(fail_str + "Error: segment_juncs not found on this system")
        die(str(o))

    return [juncs_out, insertions_out, deletions_out, fusions_out]

# Joins mapped segments into full-length read alignments via the executable
# long_spanning_reads
def join_mapped_segments(params,
                         sam_header_filename,
                         reads,
                         ref_fasta,
                         possible_juncs,
                         possible_insertions,
                         possible_deletions,
                         possible_fusions,
                         contig_seg_maps,
                         spliced_seg_maps,
                         alignments_out_name):
    rn=""
    contig_seg_maps = ','.join(contig_seg_maps)

    possible_juncs = ','.join(possible_juncs)
    possible_insertions = ",".join(possible_insertions)
    possible_deletions = ",".join(possible_deletions)
    possible_fusions = ",".join(possible_fusions)

    if resumeStage > currentStage: return
    if len(contig_seg_maps)>1:
       th_log("Joining segment hits")
       rn=".segs"
    else:
       th_log("Processing bowtie hits")
    log_fname=logging_dir + "long_spanning_reads"+rn+".log"
    align_log = open(log_fname, "w")
    align_cmd = [prog_path("long_spanning_reads")]

    align_cmd.extend(params.cmd())
    align_cmd += ["--sam-header", sam_header_filename]

    b2_params = params.bowtie2_params
    max_penalty, min_penalty = b2_params.mp.split(',')
    align_cmd += ["--bowtie2-max-penalty", max_penalty,
                  "--bowtie2-min-penalty", min_penalty]

    align_cmd += ["--bowtie2-penalty-for-N", str(b2_params.np)]

    read_gap_open, read_gap_cont = b2_params.rdg.split(',')
    align_cmd += ["--bowtie2-read-gap-open", read_gap_open,
                  "--bowtie2-read-gap-cont", read_gap_cont]

    ref_gap_open, ref_gap_cont = b2_params.rfg.split(',')
    align_cmd += ["--bowtie2-ref-gap-open", ref_gap_open,
                  "--bowtie2-ref-gap-cont", ref_gap_cont]

    align_cmd.append(ref_fasta)
    align_cmd.extend([reads,
                      possible_juncs,
                      possible_insertions,
                      possible_deletions,
                      possible_fusions,
                      alignments_out_name,
                      contig_seg_maps])

    if spliced_seg_maps:
        spliced_seg_maps = ','.join(spliced_seg_maps)
        align_cmd.append(spliced_seg_maps)

    try:
        print >> run_log, " ".join(align_cmd)
        ret = subprocess.call(align_cmd,
                                  stderr=align_log)
        if ret:
          die(fail_str+"Error running 'long_spanning_reads':"+log_tail(log_fname))
    except OSError, o:
        die(fail_str+"Error: "+str(o))

# This class collects spliced and unspliced alignments for each of the
# left and right read files provided by the user.
class Maps:
        def __init__(self,
                     unspliced_sam,
                     seg_maps,
                     unmapped_segs,
                     segs):
            self.unspliced_sam = unspliced_sam
            self.seg_maps = seg_maps
            self.unmapped_segs = unmapped_segs
            self.segs = segs

# Map2GTF stuff
def m2g_convert_coords(params, sam_header_filename, gtf_fname, reads, out_fname):
    """ajjkljlks

    Arguments:
    - `params`: TopHat parameters
    - `gtf_fname`: File name pointing to the annotation.
    - `reads`: The reads to convert coords (in Bowtie format).
    - `out_fname`: The file name pointing to the output.
    """
    m2g_cmd = [prog_path("map2gtf")]
    m2g_cmd.extend(params.cmd())
    m2g_cmd += ["--sam-header", sam_header_filename]
    m2g_cmd.append(gtf_fname)
    m2g_cmd.append(reads) #could be BAM file
    m2g_cmd.append(out_fname)
    fbasename = getFileBaseName(reads)
    m2g_log = logging_dir + "m2g_" + fbasename + ".out"
    m2g_err = logging_dir + "m2g_" + fbasename + ".err"

    try:
        th_log("Converting " + fbasename + " to genomic coordinates (map2gtf)")
        print >> run_log, " ".join(m2g_cmd) + " > " + m2g_log
        ret = subprocess.call(m2g_cmd,
                              stdout=open(m2g_log, "w"),
                              stderr=open(m2g_err, "w"))
        if ret != 0:
            die(fail_str + " Error: map2gtf returned an error")
    except OSError, o:
        err_msg = fail_str + str(o)
        die(err_msg + "\n")


def gtf_to_fasta(params, trans_gtf, genome, out_basename):
    """ Build the transcriptome data files from a GTF.

    Arguments:
    - `trans_gtf`:
    - `genome`:
    - `out_basename`:
    Returns:
    - name of the FASTA file
    """
    out_fname=out_basename + ".fa"
    out_fver=out_basename + ".ver"
    if resumeStage > currentStage and fileExists(out_fname) and fileExists(out_fver):
       return out_fname
    g2f_cmd = [prog_path("gtf_to_fasta")]
    g2f_cmd.extend(params.cmd())
    g2f_cmd.append(trans_gtf)
    g2f_cmd.append(genome)
    g2f_cmd.append(out_fname)

    g2f_log = logging_dir + "g2f.out"
    g2f_err = logging_dir + "g2f.err"

    try:
        print >> run_log, " ".join(g2f_cmd)+" > " + g2f_log
        ret = subprocess.call(g2f_cmd,
                              stdout = open(g2f_log, "w"),
                              stderr = open(g2f_err, "w"))
        if ret != 0:
            die(fail_str + " Error: gtf_to_fasta returned an error.")
    except OSError, o:
        err_msg = fail_str + str(o)
        die(err_msg + "\n")
    fver = open(out_fver, "w", 0)
    print >> fver, "%d %d %d" % (GFF_T_VER, os.path.getsize(trans_gtf), os.path.getsize(out_fname))
    fver.close()
    return out_fname

def map2gtf(params, genome_sam_header_filename, ref_fasta, left_reads, right_reads):
    """ Main GTF mapping function

    Arguments:
    - `params`: The TopHat parameters.
    - `ref_fasta`: The reference genome.
    - `left_reads`: A list of reads.
    - `right_reads`: A list of reads (empty if single-end).

    """
    test_input_file(params.gff_annotation)

    # th_log("Reading in GTF file: " + params.gff_annotation)
    # transcripts = gtf_to_transcripts(params.gff_annotation)

    gtf_name = getFileBaseName(params.gff_annotation)
    m2g_bwt_idx = None
    t_out_dir = tmp_dir
    if currentStage < resumeStage or (params.transcriptome_index and not params.transcriptome_outdir):
       m2g_bwt_idx = params.transcriptome_index
       th_log("Using pre-built transcriptome data..")
    else:
       if params.transcriptome_outdir:
         t_out_dir=params.transcriptome_outdir+"/"
       th_log("Building transcriptome data files "+t_out_dir+gtf_name)
       m2g_ref_name  = t_out_dir + gtf_name
       m2g_ref_fasta = gtf_to_fasta(params, params.gff_annotation, ref_fasta, m2g_ref_name)
       m2g_bwt_idx = build_idx_from_fa(params.bowtie2, m2g_ref_fasta, t_out_dir, params.read_params.color)
       params.transcriptome_index = m2g_bwt_idx
    if params.transcriptome_buildonly:
       return
    transcriptome_header_filename = get_index_sam_header(params, m2g_bwt_idx)

    mapped_gtf_list = []
    unmapped_gtf_list = []    
    # do the initial mapping in GTF coordinates
    for reads in [left_reads, right_reads]:
        if reads == None or os.path.getsize(reads) < 25 :
            continue
        fbasename = getFileBaseName(reads)
        mapped_gtf_out = tmp_dir + fbasename + ".m2g"
        #if use_zpacker:
        #    mapped_gtf_out+=".z"

        unmapped_gtf = tmp_dir + fbasename + ".m2g_um"
        #if use_BWT_FIFO:
        #    unmapped_gtf += ".z"

        (mapped_gtf_map, unmapped) = bowtie(params,
                                            m2g_bwt_idx,
                                            [transcriptome_header_filename, genome_sam_header_filename],
                                            [reads],
                                            params.read_mismatches,
                                            params.read_gap_length,
                                            params.read_edit_dist,
                                            params.read_realign_edit_dist,
                                            mapped_gtf_out,
                                            unmapped_gtf,
                                            "", _reads_vs_T)
        mapped_gtf_list.append(mapped_gtf_map)
        unmapped_gtf_list.append(unmapped)

    if len(mapped_gtf_list) < 2:
        mapped_gtf_list.append(None)
    if len(unmapped_gtf_list) < 2:
        unmapped_gtf_list.append(None)
    return (mapped_gtf_list, unmapped_gtf_list)
# end Map2GTF

def get_preflt_data(params, ri, target_reads, out_mappings, out_unmapped):
 ## extract mappings and unmapped reads from prefilter mappings and preflt_ium
 ##
 #this is accomplished by a special prep_reads usage (triggered by --flt-hits)
 out_bam=None
 #if params.read_params.color:
 #  out_unmapped += ".fq"
 #  #if use_zpacker: out_unmapped += ".z"
 #else:
 out_unmapped += ".bam"
 out_bam = out_unmapped
 # no colorspace reads
 if resumeStage:
     return (out_mappings, out_unmapped)
 do_use_zpacker = use_zpacker and not out_bam
 prep_cmd=prep_reads_cmd(params, params.preflt_data[ri].unmapped_reads, None,
                     None, None, # right-side mates
                     out_bam, # stdout file
                     out_mappings, # aux file (filtered mappings)
                     None, # no index for out_bam
                     [target_reads], # prefilter reads
                     [params.preflt_data[ri].mappings]) # mappings to filter
 if not out_bam: um_reads = open(out_unmapped, "wb")
 sides=["left","right"]
 log_fname=logging_dir + "prep_reads.from_preflt."+sides[ri]+".log"
 filter_log = open(log_fname,"w")

 shell_cmd = " ".join(prep_cmd)
 #add the compression pipe
 zip_cmd=[]
 if do_use_zpacker:
    zip_cmd=[ params.system_params.zipper ]
    zip_cmd.extend(params.system_params.zipper_opts)
    zip_cmd.extend(['-c','-'])
    shell_cmd +=' | '+' '.join(zip_cmd)
 if not out_bam:
    shell_cmd += ' >' + out_unmapped
 retcode=0
 try:
     print >> run_log, shell_cmd
     if do_use_zpacker:
         prep_proc = subprocess.Popen(prep_cmd,
                               stdout=subprocess.PIPE,
                               stderr=filter_log)
         zip_proc = subprocess.Popen(zip_cmd,
                               preexec_fn=subprocess_setup,
                               stdin=prep_proc.stdout,
                               stderr=tophat_log, stdout=um_reads)
         prep_proc.stdout.close() #as per http://bugs.python.org/issue7678
         zip_proc.communicate()
         retcode=prep_proc.poll()
         if retcode==0:
           retcode=zip_proc.poll()
     else:
         if out_bam:
             retcode = subprocess.call(prep_cmd, stderr=filter_log)
         else:
             retcode = subprocess.call(prep_cmd, stdout=um_reads,
                              stderr=filter_log)
     if retcode:
         die(fail_str+"Error running 'prep_reads'\n"+log_tail(log_fname))

 except OSError, o:
     errmsg=fail_str+str(o)
     die(errmsg+"\n"+log_tail(log_fname))
 if not out_bam: um_reads.close()

 return (out_mappings, out_unmapped)


# The main aligment routine of TopHat.  This function executes most of the
# workflow producing a set of candidate alignments for each cDNA fragment in a
# pair of SAM alignment files (for paired end reads).
def spliced_alignment(params,
                      bwt_idx_prefix,
                      sam_header_filename,
                      ref_fasta,
                      read_len,
                      segment_len,
                      prepared_reads,
                      user_supplied_junctions,
                      user_supplied_insertions,
                      user_supplied_deletions):

    possible_juncs = []
    possible_juncs.extend(user_supplied_junctions)

    possible_insertions = []
    possible_insertions.extend(user_supplied_insertions)
    possible_deletions = []
    possible_deletions.extend(user_supplied_deletions)
    possible_fusions = []

    left_reads, right_reads = prepared_reads

    maps = [[], []] # maps[0] = left_reads mapping data, maps[1] = right_reads_mapping_data
    # Before anything, map the reads using Map2GTF (if using annotation)
    m2g_maps = [ None, None ] # left, right
    initial_reads = [ left_reads, right_reads ]
    setRunStage(_stage_map_start)

    if params.gff_annotation:
        (mapped_gtf_list, unmapped_gtf_list) = \
            map2gtf(params, sam_header_filename, ref_fasta, left_reads, right_reads)

        m2g_left_maps, m2g_right_maps = mapped_gtf_list
        m2g_maps = [m2g_left_maps, m2g_right_maps]
        if params.transcriptome_only or not fileExists(unmapped_gtf_list[0]):
            # The case where the user doesn't want to map to anything other
            # than the transcriptome OR we have no unmapped reads
            maps[0] = [m2g_left_maps]
            if right_reads:
                maps[1] = [m2g_right_maps]

            return maps
        # Feed the unmapped reads into spliced_alignment()
        initial_reads = unmapped_gtf_list[:]
        if currentStage >= resumeStage:
           th_log("Resuming TopHat pipeline with unmapped reads")

        if not nonzeroFile(initial_reads[0]) and \
                (not initial_reads[1] or not nonzeroFile(initial_reads[1])):

            if m2g_maps[1]:
                return [[m2g_maps[0]], [m2g_maps[1]]]
            else:
                return [[m2g_maps[0]], []]

    max_seg_len = segment_len #this is the ref seq span on either side of the junctions
                              #to be extracted into segment_juncs.fa

    num_segs = int(read_len / segment_len)
    if (read_len % segment_len) >= min(segment_len-2, 20):
        #remainder is shorter but long enough to become a new segment
        num_segs += 1
    else:
       # the last segment is longer
       if num_segs>1: max_seg_len += (read_len % segment_len)

    if num_segs <= 1:
         th_logp("Warning: you have only one segment per read.\n\tIf the read length is greater than or equal to 45bp,\n\twe strongly recommend that you decrease --segment-length to about half the read length because TopHat will work better with multiple segments")

    # Using the num_segs value returned by check_reads(),
    # decide which junction discovery strategy to use
    if num_segs < 3:
       #if params.butterfly_search != False:
       #   params.butterfly_search = True
       if params.coverage_search != False:
           params.coverage_search = True
       if num_segs == 1:
         segment_len = read_len
    else: #num_segs >= 3:
        # if we have at least three segments, just use split segment search,
        # which is the most sensitive and specific, fastest, and lightest-weight.
        # so unless specifically requested, disable the other junction searches
        if params.closure_search != True:
               params.closure_search = False
        if params.coverage_search != True:
               params.coverage_search = False
        if params.butterfly_search != True:
                params.butterfly_search = False

    # Perform the first part of the TopHat work flow on the left and right
    # reads of paired ends separately - we'll use the pairing information later
    have_left_IUM = False
    for ri in (0,1):
        reads=initial_reads[ri]
        if reads == None or not nonzeroFile(reads):
            continue

        fbasename=getFileBaseName(reads)
        unspliced_out = tmp_dir + fbasename + ".mapped"
        unspliced_sam = None
        unmapped_reads = None
        #if use_zpacker: unspliced_out+=".z"
        unmapped_unspliced = tmp_dir + fbasename + "_unmapped"
        if params.prefilter_multi:
          #unmapped_unspliced += ".z"
          (unspliced_sam, unmapped_reads) = get_preflt_data(params, ri, reads, unspliced_out, unmapped_unspliced)
        else:
        # Perform the initial Bowtie mapping of the full length reads
          (unspliced_sam, unmapped_reads) = bowtie(params,
                                                   bwt_idx_prefix,
                                                   sam_header_filename,
                                                   [reads],
                                                   params.read_mismatches,
                                                   params.read_gap_length,
                                                   params.read_edit_dist,
                                                   params.read_realign_edit_dist,
                                                   unspliced_out,
                                                   unmapped_unspliced,
                                                   "",
                                                   _reads_vs_G)

        seg_maps = []
        unmapped_segs = []
        segs = []

        have_IUM = nonzeroFile(unmapped_reads)
        if ri==0 and have_IUM:
           have_left_IUM = True
        setRunStage(_stage_map_segments)
        if num_segs > 1 and have_IUM:
            # split up the IUM reads into segments
            # unmapped_reads can be in BAM format
            read_segments = split_reads(unmapped_reads,
                                        tmp_dir + fbasename,
                                        False,
                                        params,
                                        segment_len)

            # Map each segment file independently with Bowtie
            for i in range(len(read_segments)):
                seg = read_segments[i]
                fbasename=getFileBaseName(seg)
                seg_out =  tmp_dir + fbasename
                unmapped_seg = tmp_dir + fbasename + "_unmapped"
                extra_output = "(%d/%d)" % (i+1, len(read_segments))
                (seg_map, unmapped) = bowtie(params,
                                             bwt_idx_prefix,
                                             sam_header_filename,
                                             [seg],
                                             params.segment_mismatches,
                                             params.segment_mismatches,
                                             params.segment_mismatches,
                                             params.segment_mismatches,
                                             seg_out,
                                             unmapped_seg,
                                             extra_output,
                                             _segs_vs_G)
                seg_maps.append(seg_map)
                unmapped_segs.append(unmapped)
                segs.append(seg)

            # Collect the segment maps for left and right reads together
            maps[ri] = Maps(unspliced_sam, seg_maps, unmapped_segs, segs)
        else:
            # if there's only one segment, just collect the initial map as the only
            # map to be used downstream for coverage-based junction discovery
            read_segments = [reads]
            maps[ri] = Maps(unspliced_sam, [unspliced_sam], [unmapped_reads], [unmapped_reads])

    # XXX: At this point if using M2G, have three sets of reads:
    # mapped to transcriptome, mapped to genome, and unmapped (potentially
    # spliced or poly-A tails) - hp
    unmapped_reads = []
    if maps[0]:
        left_reads_map = maps[0].unspliced_sam
        left_seg_maps = maps[0].seg_maps
        unmapped_reads = maps[0].unmapped_segs
    else:
        left_reads_map = None
        left_seg_maps = None

    if right_reads and maps[1]:
        right_reads_map = maps[1].unspliced_sam
        right_seg_maps = maps[1].seg_maps
        unmapped_reads.extend(maps[1].unmapped_segs)
    else:
        right_reads_map = None
        right_seg_maps = None

    if params.find_novel_juncs and have_left_IUM: # or params.find_novel_indels:
        # Call segment_juncs to infer a list of possible splice junctions from
        # the regions of the genome covered in the initial and segment maps
        #if params.find_novel_juncs:
        #TODO: in m2g case, we might want to pass the m2g mappings as well,
        #      or perhaps the GTF file directly
        #      -> this could improve alternative junction detection?
        setRunStage(_stage_find_juncs)
        juncs = junctions_from_segments(params,
                                        sam_header_filename,
                                        left_reads,
                                        left_reads_map,
                                        left_seg_maps,
                                        right_reads,
                                        right_reads_map,
                                        right_seg_maps,
                                        unmapped_reads,
                                        ref_fasta)

        if not params.system_params.keep_tmp:
            for unmapped_seg in unmapped_reads:
                removeFileWithIndex(unmapped_seg)

        if os.path.getsize(juncs[0]) != 0:
            possible_juncs.append(juncs[0])
        if params.find_novel_indels:
            if os.path.getsize(juncs[1]) != 0:
                possible_insertions.append(juncs[1])
            if os.path.getsize(juncs[2]) != 0:
                possible_deletions.append(juncs[2])
        if params.find_novel_fusions:
            if os.path.getsize(juncs[3]) != 0:
                possible_fusions.append(juncs[3])
        # Optionally, and for paired reads only, use a closure search to
        # discover addtional junctions
        if currentStage >= resumeStage and params.closure_search and left_reads and right_reads:
            juncs = junctions_from_closures(params,
                                            sam_header_filename,
                                            [maps[initial_reads[left_reads]].unspliced_sam, maps[initial_reads[left_reads]].seg_maps[-1]],
                                            [maps[initial_reads[right_reads]].unspliced_sam, maps[initial_reads[right_reads]].seg_maps[-1]],
                                            ref_fasta)
            if os.path.getsize(juncs[0]) != 0:
                possible_juncs.extend(juncs)

    if len(possible_insertions) == 0 and len(possible_deletions) == 0 and len(possible_juncs) == 0 and len(possible_fusions) == 0:
        spliced_seg_maps = None
        junc_idx_prefix = None
    else:
        junc_idx_prefix = "segment_juncs"
    if len(possible_insertions) == 0:
        possible_insertions.append(os.devnull)
        # print >> sys.stderr, "Warning: insertions database is empty!"
    if len(possible_deletions) == 0:
        possible_deletions.append(os.devnull)
        # print >> sys.stderr, "Warning: deletions database is empty!"
    if len(possible_juncs) == 0:
        possible_juncs.append(os.devnull)
        th_logp("Warning: junction database is empty!")
    if len(possible_fusions) == 0:
        possible_fusions.append(os.devnull)

    setRunStage(_stage_juncs_db)
    juncs_bwt_samheader = None
    juncs_bwt_idx = None
    if junc_idx_prefix:
        jdb_prefix  = tmp_dir + junc_idx_prefix
        if currentStage<resumeStage and fileExists(jdb_prefix + ".fa"):
           juncs_bwt_idx = jdb_prefix
        else:
           juncs_bwt_idx = build_juncs_index(params.bowtie2,
                                          3,
                                          max_seg_len,
                                          junc_idx_prefix,
                                          possible_juncs,
                                          possible_insertions,
                                          possible_deletions,
                                          possible_fusions,
                                          ref_fasta,
                                          params.read_params.color)
        juncs_bwt_samheader = get_index_sam_header(params, juncs_bwt_idx)

    # Now map read segments (or whole IUM reads, if num_segs == 1) to the splice
    # index with Bowtie
    setRunStage(_stage_map2juncs)
    for ri in (0,1):
        reads = initial_reads[ri]
        if not reads: continue
        spliced_seg_maps = []
        rfname=getFileBaseName(reads)
        rfdir=getFileDir(reads)

        m2g_map = m2g_maps[ri]
        mapped_reads = rfdir + rfname + ".candidates.bam"
        merged_map = rfdir + rfname + ".candidates_and_unspl.bam"

        if maps[ri]:
            unspl_samfile = maps[ri].unspliced_sam
        else:
            unspl_samfile = None

        have_IUM = True
        if reads == None or not nonzeroFile(reads):
            have_IUM = False

        if have_IUM:
            if junc_idx_prefix:
                i = 0
                for seg in maps[ri].segs:
                    #search each segment
                    fsegname = getFileBaseName(seg)
                    seg_out = tmp_dir + fsegname + ".to_spliced"
                    extra_output = "(%d/%d)" % (i+1, len(maps[ri].segs))
                    (seg_map, unmapped) = bowtie(params,
                                                 tmp_dir + junc_idx_prefix,
                                                 juncs_bwt_samheader,
                                                 [seg],
                                                 params.segment_mismatches,
                                                 params.segment_mismatches,
                                                 params.segment_mismatches,
                                                 params.segment_mismatches,
                                                 seg_out,
                                                 None,
                                                 extra_output,
                                                 _segs_vs_J)
                    spliced_seg_maps.append(seg_map)
                    i += 1

                # Join the contigous and spliced segment hits into full length
                #   read alignments
                # -- spliced mappings built from all segment mappings vs genome and junc_db
                join_mapped_segments(params,
                                     sam_header_filename,
                                     reads,
                                     ref_fasta,
                                     possible_juncs,
                                     possible_insertions,
                                     possible_deletions,
                                     possible_fusions,
                                     maps[ri].seg_maps,
                                     spliced_seg_maps,
                                     mapped_reads)
                #if not params.system_params.keep_tmp:
                #    for seg_map in maps[ri].seg_maps:
                #        removeFileWithIndex(seg_map)
                #    for spliced_seg_map in spliced_seg_maps:
                #        removeFileWithIndex(spliced_seg_map)
        maps[ri] = []
        if m2g_map and \
               nonzeroFile(m2g_map):
            maps[ri].append(m2g_map)

        if unspl_samfile and \
               nonzeroFile(unspl_samfile):
            maps[ri].append(unspl_samfile)

        if mapped_reads and nonzeroFile(mapped_reads):
            maps[ri].append(mapped_reads)
        else:
            for bam_i in range(0, params.system_params.num_threads):
                temp_bam = mapped_reads[:-4] + str(bam_i) + ".bam"
                if nonzeroFile(temp_bam):
                    maps[ri].append(mapped_reads[:-4])
                    break

    return maps

# rough equivalent of the 'which' command to find external programs
# (current script path is tested first, then PATH envvar)
def which(program):
    def is_executable(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)
    fpath, fname = os.path.split(program)
    if fpath:
        if is_executable(program):
            return program
    else:
        progpath = os.path.join(bin_dir, program)
        if is_executable(progpath):
           return progpath
        for path in os.environ["PATH"].split(os.pathsep):
           progpath = os.path.join(path, program)
           if is_executable(progpath):
              return progpath
    return None

def prog_path(program):
    progpath=which(program)
    if progpath == None:
        die("Error locating program: "+program)
    return progpath

def get_version():
   return "__VERSION__"

def mlog(msg):
  print >> sys.stderr, "[DBGLOG]:"+msg

def test_input_file(filename):
    try:
        test_file = open(filename, "r")
    except IOError:
        die("Error: Opening file %s" % filename)
    return

def validate_transcriptome(params):
 tgff=params.transcriptome_index+".gff"
 if os.path.exists(tgff):
   if params.gff_annotation and tgff!=params.gff_annotation:
       if (os.path.getsize(tgff)!=os.path.getsize(params.gff_annotation)):
         return False
   tfa=params.transcriptome_index+".fa"
   tverf=params.transcriptome_index+".ver"
   tver=0
   tfa_size=0
   tgff_size=0
   if os.path.exists(tverf):
     inf = open(tverf, 'r')
     fline = inf.readline()
     inf.close()
     dlst = fline.split()
     if len(dlst)>2:
         tver, tgff_size, tfa_size = map(lambda f: int(f), dlst)
   else:
     return False
   tlst=tfa+".tlst"
   if os.path.exists(tlst) and os.path.getsize(tlst)>0 and \
      os.path.exists(tfa) and os.path.getsize(tfa)>0 and os.path.getsize(tfa)== tfa_size and \
      os.path.exists(tgff) and os.path.getsize(tgff)>0 and os.path.getsize(tgff)==tgff_size \
      and tver >= GFF_T_VER:
        return True
 return False

def main(argv=None):
    warnings.filterwarnings("ignore", "tmpnam is a potential security risk")

    # Initialize default parameter values
    params = TopHatParams()
    run_argv = sys.argv[:]
    try:
        if argv is None:
            argv = sys.argv
        args = params.parse_options(argv)
        if params.resume_dir:
            run_argv=doResume(params.resume_dir)
            args = params.parse_options(run_argv)
        params.check()

        bwt_idx_prefix = args[0]
        left_reads_list = None
        if len(args)>1:
          left_reads_list = args[1]
        left_quals_list, right_quals_list = None, None
        if (not params.read_params.quals and len(args) > 2) or (params.read_params.quals and len(args) > 3):
            if params.read_params.mate_inner_dist == None:
                params.read_params.mate_inner_dist = 50
                #die("Error: you must set the mean inner distance between mates with -r")

            right_reads_list = args[2]
            if params.read_params.quals:
                left_quals_list = args[3]
                right_quals_list = args[4]
        else:
            right_reads_list = None
            if params.read_params.quals:
                left_quals_list = args[2]

        start_time = datetime.now()
        
        prepare_output_dir()
        init_logger(logging_dir + "tophat.log")

        th_logp()
        if resumeStage>0:
           th_log("Resuming TopHat run in directory '"+output_dir+"' stage '"+stageNames[resumeStage]+"'")
        else:
           if params.transcriptome_buildonly:
             th_log("Building transcriptome files with TopHat v"+get_version())
           else:
             th_log("Beginning TopHat run (v"+get_version()+")")
        th_logp("-----------------------------------------------")

        global run_log
        run_log = open(logging_dir + "run.log", "w", 0)
        global run_cmd
        run_cmd = " ".join(run_argv)
        print >> run_log, run_cmd

        check_bowtie(params)
        check_samtools()

        # Validate all the input files, check all prereqs before committing
        # to the run
        if params.gff_annotation:
           if not os.path.exists(params.gff_annotation):
             die("Error: cannot find transcript file %s" % params.gff_annotation)
           if os.path.getsize(params.gff_annotation)<10:
             die("Error: invalid transcript file %s" % params.gff_annotation)

        if params.transcriptome_index:
           if params.gff_annotation:
               #gff file given, so transcriptome data will be written there
               gff_basename = getFileBaseName(params.gff_annotation)
               #just in case, check if it's not already there (-G/--GTF given again by mistake)
               tpath, tname = os.path.split(params.transcriptome_index)
               new_subdir=False
               if tpath in (".", "./") or not tpath :
                  if not os.path.exists(params.transcriptome_index):
                    os.makedirs(params.transcriptome_index)
                    new_subdir=True
               if new_subdir or (os.path.exists(params.transcriptome_index) and os.path.isdir(params.transcriptome_index)):
                   params.transcriptome_index = os.path.join(params.transcriptome_index, gff_basename)
           if not validate_transcriptome(params):
                  #(re)generate the transcriptome data files
                  tpath, tname = os.path.split(params.transcriptome_index)
                  params.transcriptome_outdir=tpath
           t_gff=params.transcriptome_index+".gff"
           if params.transcriptome_outdir:
              #will create the transcriptome data files
              if not os.path.exists(params.transcriptome_outdir):
                os.makedirs(params.transcriptome_outdir)
              if params.gff_annotation:
                   copy(params.gff_annotation, t_gff)
           else:
              #try to use existing transcriptome data files
              #if validate_transcriptome(params):
              check_bowtie_index(params.transcriptome_index, params.bowtie2, "(transcriptome)")
           params.gff_annotation = t_gff
           #end @ transcriptome_index given

        (ref_fasta, ref_seq_dict) = check_index(bwt_idx_prefix, params.bowtie2)
        if params.transcriptome_buildonly:
             map2gtf(params, "", ref_fasta, [], [])
             th_logp("-----------------------------------------------")
             th_log("Transcriptome files prepared. This was the only task requested.")
             return
        if currentStage >= resumeStage:
           th_log("Generating SAM header for "+bwt_idx_prefix)
        # we need to provide another name for this sam header as genome and transcriptome may have the same prefix.
        sam_header_filename = get_index_sam_header(params, bwt_idx_prefix, "genome")
        params.sam_header = sam_header_filename
        #if not params.skip_check_reads:
        reads_list = left_reads_list
        if right_reads_list:
                reads_list = reads_list + "," + right_reads_list
        params.read_params = check_reads_format(params, reads_list)

        user_supplied_juncs = []
        user_supplied_insertions = []
        user_supplied_deletions = []
        user_supplied_fusions = []
        global gtf_juncs
        if params.gff_annotation and params.find_GFF_juncs:
            test_input_file(params.gff_annotation)
            (found_juncs, gtf_juncs) = get_gtf_juncs(params.gff_annotation)
            ##-- we shouldn't need these junctions in user_supplied_juncs anymore because now map2gtf does a much better job
            ## but we still need them loaded in gtf_juncs for later splice verification
            if found_juncs:
                ## and not params.gff_annotation:
                user_supplied_juncs.append(gtf_juncs)
            #else:
            #    gtf_juncs = None
        if params.raw_junctions:
            test_input_file(params.raw_junctions)
            user_supplied_juncs.append(params.raw_junctions)

        if params.raw_insertions:
            test_input_file(params.raw_insertions)
            user_supplied_insertions.append(params.raw_insertions)

        if params.raw_deletions:
            test_input_file(params.raw_deletions)
            user_supplied_deletions.append(params.raw_deletions)

        global unmapped_reads_fifo
        unmapped_reads_fifo = tmp_dir + str(os.getpid())+".bwt_unmapped.z.fifo"

        # Now start the time consuming stuff
        if params.prefilter_multi:
            sides=("left","right")
            read_lists=(left_reads_list, right_reads_list)
            qual_lists=(left_quals_list, right_quals_list)
            for ri in (0,1):
               reads_list=read_lists[ri]
               if not reads_list:
                  continue
               fmulti_ext="bam"
               if not params.bowtie2:
                 fmulti_ext="fq"
               params.preflt_data[ri].seqfiles = reads_list
               params.preflt_data[ri].qualfiles = qual_lists[ri]
               params.preflt_data[ri].multihit_reads = tmp_dir + sides[ri]+"_multimapped."+fmulti_ext
               side_imap = tmp_dir + sides[ri]+"_im"
               #if use_zpacker: side_imap+=".z"
               side_ium = tmp_dir + sides[ri]+"_ium"
               #if use_BWT_FIFO and not params.bowtie2:
               #   side_ium += ".z"
               th_log("Pre-filtering multi-mapped "+sides[ri]+" reads")
               rdlist=reads_list.split(',')
               bwt=bowtie(params, bwt_idx_prefix, sam_header_filename, rdlist,
                          # params.read_params.reads_format,
                          params.read_mismatches,
                          params.read_gap_length,
                          params.read_edit_dist,
                          params.read_realign_edit_dist,
                          side_imap, side_ium,
                          "", _reads_vs_G,  ri )             #  multi-mapped reads will be in params.preflt_data[ri].multihit_reads
               params.preflt_data[ri].mappings = bwt[0] # initial mappings
               params.preflt_data[ri].unmapped_reads = bwt[1] # IUM reads

        setRunStage(_stage_prep)
        prep_info=None
        if currentStage >= resumeStage:
             th_log("Preparing reads")
        else:
             th_log("Prepared reads:")
        multihit_reads = []
        if params.preflt_data[0].multihit_reads:
           multihit_reads += [params.preflt_data[0].multihit_reads]
        if params.preflt_data[1].multihit_reads:
           multihit_reads += [params.preflt_data[1].multihit_reads]
        prep_info= prep_reads(params,
                         left_reads_list, left_quals_list,
                         right_reads_list, right_quals_list,
                         multihit_reads)
        if currentStage < resumeStage and not fileExists(prep_info.kept_reads[0],40):
             die("Error: prepared reads file missing, cannot resume!")

        min_read_len = prep_info.min_len[0]
        if prep_info.min_len[1] > 0 and min_read_len > prep_info.min_len[1]:
           min_read_len = prep_info.min_len[1]
        if min_read_len < 20:
                  th_logp("Warning: short reads (<20bp) will make TopHat quite slow and take large amount of memory because they are likely to be mapped in too many places")

        max_read_len=max(prep_info.max_len[0], prep_info.max_len[1])

        seed_len=params.read_params.seed_length
        if seed_len: #if read len was explicitly given
            seed_len = max(seed_len, min_read_len)
            #can't be smaller than minimum length observed
        else:
            seed_len = max_read_len
        params.read_params.seed_length=seed_len
        # turn off integer-quals
        if params.read_params.integer_quals:
            params.read_params.integer_quals = False

        input_reads = prep_info.kept_reads[:]
        mappings = spliced_alignment(params,
                              bwt_idx_prefix,
                              sam_header_filename,
                              ref_fasta,
                              params.read_params.seed_length,
                              params.segment_length,
                              input_reads,
                              user_supplied_juncs,
                              user_supplied_insertions,
                              user_supplied_deletions)
        setRunStage(_stage_tophat_reports)

        compile_reports(params,
                        sam_header_filename,
                        ref_fasta,
                        mappings,
                        input_reads,
                        params.gff_annotation)

        setRunStage(_stage_alldone)

        if not params.system_params.keep_tmp:
            try:
              s=tmp_dir.rstrip('/')
              rmtree(s, True)
            except OSError:
              pass
              #th_logp("Warning: couldn't remove all temporary files in "+tmp_dir)
        finish_time = datetime.now()
        duration = finish_time - start_time


        th_logp("-----------------------------------------------")
        th_log("A summary of the alignment counts can be found in %salign_summary.txt" % output_dir)
        th_log("Run complete: %s elapsed" %  formatTD(duration))

    except Usage, err:
        th_logp(sys.argv[0].split("/")[-1] + ": " + str(err.msg))
        th_logp("    for detailed help see http://ccb.jhu.edu/software/tophat/manual.shtml")
        return 2


if __name__ == "__main__":
    sys.exit(main())
