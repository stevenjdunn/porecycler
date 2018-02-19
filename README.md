# PoreCycler
**Hands free MinION data processing using Porechop for barcode trimming/binning, and Unicycler for assembly.**

An automated assembly pipeline based on the amazing work by Ryan Wick:
- Unicycler - https://github.com/rrwick/Unicycler
- Porechop - https://github.com/rrwick/Porechop

https://doi.org/10.1371/journal.pcbi.1005595

 ## Dependencies
 - Unicycler
 - Porechop
 
 ## Quick Start
 Input requirements:
 - MinION fastq reads generated by Albacore's read_fast5_basecaller.py
 - CSV (comma separated text file) containing barcodes used and desired sample names (e.g. NB01, Sample1)

**MinION Assembly:**
 
     porecycler.py -i input.txt -f ~/path_to/albacore_fastqs -o ~/output/path 
     
**MinION + Illumina Hybrid Assembly:**
 
     porecycler.py -i input.txt -f ~/path_to/albacore_fastqs -o ~/output/path -hyb -s ~/path_to/Illumina_reads

 ## Usage: 
 
    minion.py [-h] -i INPUT -f FASTQ -o OUTPUT [-p] [-hyb] [-s SBS] [-c]
                 [-m] [-cons] [-bold]

    Hands free MinION data processing using Porechop for barcode trimming/binning,
    and Unicycler for assembly.

    optional arguments:
      -h, --help            show this help message and exit
      -p, --porechop        Run porechop and rename/collect files only (i.e. no
                            assembly)
      -hyb, --hybrid        Specifies hybrid assembly, expects input file to
                            contain filenames of paired end illumina reads.
      -s SBS, --sbs SBS     Path to directory containing Illumina read files.
      -c, --call            Invoke porechop on reads identified as 'Unclassified'
                            by Albacore
      -m, --merge           Merges 'Unclassified' reads succesfully demultiplexed
                            by Porechop with consensus read files
      -cons, --conservative
                            Runs unicycler in conservative mode.
      -bold, --bold         Runs unicycler in bold mode.

    required arguments:
      -i INPUT, --input INPUT
                            Path to CSV file containing list of barcodes and their
                            corresponding sample name.
      -f FASTQ, --fastq FASTQ
                            Path to directory containing raw basecalled data
                            generated by Albacore in fastq format
      -o OUTPUT, --output OUTPUT
                            Path to output destination
      
 
 ## Input CSV File
 PoreCycler requires you to provide it with an input file listing all of the barcodes used and the desired output sample names. 
 
 **e.g. CSV layout for a long-read only assembly:**
 
     NB01, Sample_1
     NB02, Sample_2
     NB03, Sample_3
 
If you want to perform a hybrid assembly, you will also need to provide the filenames of your forward and reverse paired-end Illumina reads. Please note you will need to use the -hyb flag, and point PoreCycler to the directory containing your Illumina reads using the -s flag. To easily generate a list of R1 and R2 file names, you can use ls:

     ls *_1* >> R1.txt && ls *_2* >> R2.txt
     
**e.g.CSV layout for a hybrid assembly:**
     
     NB01, Sample_1, S01_Illumina_read_1.fastq, S01_Illumina_read_2.fastq
     NB02, Sample_2, S02_Illumina_read_1.fastq, S02_Illumina_read_2.fastq
     NB03, Sample_3, S03_Illumina_read_1.fastq, S03_Illumina_read_2.fastq

## Bridging Mode
By default, unicyler will run in 'Normal' mode. To run Unicycler in Conservative mode, use the '-cons' flag. To run Unicycler in Bold mode, use the '-bold' flag. For a brief outline of what these modes do, please see the following table adapted from Unicycler's github page:

Bridging Mode| Usage                                | Bridging Quality Cutoff | Contig Merging
------------ | ------------------------------------ | ------------------------ | -------------------------------------
conservative | `‑cons`                              | high (25)                | Only merged with bridges
normal       | `default`                            | medium (10)              | Merged with bridges & multiplicity = 1
bold         | `‑bold`                              | low (1)                  | Merged wherever possible

Uniycler is blessed by great documentation, if you want to know more about how it bridges contigs please visit: https://github.com/rrwick/Unicycler#conservative-normal-and-bold

 ## Unclassified Reads
 During basecalling, Albacore will output all reads it was not able to sucessfully demultiplex in the 'unclassified' directory. By default, PoreCycler ignores these reads, and instead uses Porechop to repeat the barcode binning and create a consensual file. These resulting assembly will therefore be constructed of demultiplexed reads that both Albacore *and* porechop agree on.  
 
 You can also choose to process the unclassified reads using porechop using the '-c' or '--call' flag for manual inspection. If you want to include these reads in the assembly, use the '-m' or '--merge' flag, which will concatenate the consensual reads and unclassified reads into a final fastq before running unicycler. Please note that by doing this, you are losing the consensus between Albacore and Porechop, and introducing a number of non-consensual reads.
 
 ## Questions
 **I'm getting an error, what should I do?**
 
 I tried to write as many verbose error messages as possible at points where I think failure could occur. Some of them should explain the problem, others will just print a general error. It's worth reading over the PoreCycler.log file to see what happened - there are occasional # codes (e.g. #E1) to trace the error to a particular line of the script. 
 
 Check you have enough disk space, that you have read and write permissions on the target path, and that everything in your input file is correct. If you can't diagnose the issue yourself, raise an issue and attach your input file and PoreCycler.log. 
 
**Why did you do X with Y in Z way?**

Because I am inexperienced and write code to fix my own problems before packaging in a slightly neater way. I code on the train during my commute with limited internet access, so I can only sporadically check StackOverflow answers for my limitless questions. I’m sure 90% of my code can be achieved in a neater and more pythonic way. I won't be ofended if you make a pull request and school me!
 
## Pipeline Overview
![alt text](https://i.imgur.com/Hb6kpjS.png)
