# XNAT Tagger (beta)
xnattagger is a command line tool that adds tags to the note field of MR Session scans on XNAT. Tagging the 
scans is a necessary precursor to running the [`anatqc`](https://github.com/harvard-nrg/anatqc), t2qc and dwiqc pipelines.


# Usage

xnat_tagger.py --alias <xnat alias> --target <modality (t1, t2, dwi, all)> session <MRsession label>
