# bibtidy

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that verifies each BibTeX entry exists and checks its metadata against publisher databases — catching wrong authors, wrong years, stale arXiv preprints, and incorrect page numbers.

## Install

From the plugin marketplace:
```
/plugin marketplace add mathpluscode/bibtidy
/plugin install bibtidy@bibtidy
```

## Usage

```
/bibtidy refs.bib
```

bibtidy verifies each entry against [Google Scholar](https://scholar.google.com/) and [CrossRef](https://search.crossref.org/), fixes errors, and upgrades stale preprints to published versions. Every change includes the original entry commented out above so you can compare or revert, plus a `% bibtidy: source` URL for verification. We recommend using git to track changes. If using [Overleaf](https://www.overleaf.com/), this can be done with [git sync](https://docs.overleaf.com/integrations-and-add-ons/git-integration-and-github-synchronization).

To remove bibtidy comments after review, ask Claude: "remove all bibtidy comments from refs.bib"

## Examples

<details open>
<summary><b>Example 1</b>: Google Scholar adds editors as co-authors (<a href="https://scholar.googleusercontent.com/scholar.bib?q=info:Rt8ZJ9wqQacJ:scholar.google.com/&output=citation&scisdr=Cjzimnz0EKWmm3JEMfU:ADi0EEUAAAAAab9CKfWxrzWAi-uVwDbMLutl1_s&scisig=ADi0EEUAAAAAab9CKVjijw6BW7-dGJr1fECB9uQ&scisf=4&ct=citation&cd=-1&hl=en">source</a>)</summary>

Before:
```bibtex
@article{hyvarinen2005estimation,
  title={Estimation of non-normalized statistical models by score matching.},
  author={Hyv{\"a}rinen, Aapo and Dayan, Peter},
  journal={Journal of Machine Learning Research},
  volume={6},
  number={4},
  year={2005}
}
```

After:
```bibtex
% @article{hyvarinen2005estimation,
%   title={Estimation of non-normalized statistical models by score matching.},
%   author={Hyv{\"a}rinen, Aapo and Dayan, Peter},
%   journal={Journal of Machine Learning Research},
%   volume={6},
%   number={4},
%   year={2005}
% }
% bibtidy: source https://jmlr.org/papers/v6/hyvarinen05a.html
% bibtidy: removed "Dayan, Peter" — journal editor, not co-author; number 4 → 24; added pages 695--709
@article{hyvarinen2005estimation,
  title={Estimation of non-normalized statistical models by score matching},
  author={Hyv{\"a}rinen, Aapo},
  journal={Journal of Machine Learning Research},
  volume={6},
  number={24},
  pages={695--709},
  year={2005}
}
```

</details>

<details open>
<summary><b>Example 2</b>: arXiv preprint upgraded to published version (<a href="https://scholar.googleusercontent.com/scholar.bib?q=info:sCeCG7MKl-EJ:scholar.google.com/&output=citation&scisdr=Cjzimnz0EKWmm3JEcQ8:ADi0EEUAAAAAab9CaQ_kXDvxa7JtfZRV_Nw4PHA&scisig=ADi0EEUAAAAAab9CaYN4q4ZlyBKVAwVYN49_U9k&scisf=4&ct=citation&cd=-1&hl=en">source</a>)</summary>

Before:
```bibtex
@article{lipman2022flow,
  title={Flow matching for generative modeling},
  author={Lipman, Yaron and Chen, Ricky TQ and Ben-Hamu, Heli and Nickel, Maximilian and Le, Matt},
  journal={arXiv preprint arXiv:2210.02747},
  year={2022}
}
```

After:
```bibtex
% @article{lipman2022flow,
%   title={Flow matching for generative modeling},
%   author={Lipman, Yaron and Chen, Ricky TQ and Ben-Hamu, Heli and Nickel, Maximilian and Le, Matt},
%   journal={arXiv preprint arXiv:2210.02747},
%   year={2022}
% }
% bibtidy: source https://openreview.net/forum?id=PqvMRDCJT9t
% bibtidy: published at ICLR 2023 (was arXiv preprint)
@inproceedings{lipman2022flow,
  title={Flow matching for generative modeling},
  author={Lipman, Yaron and Chen, Ricky TQ and Ben-Hamu, Heli and Nickel, Maximilian and Le, Matt},
  booktitle={International Conference on Learning Representations},
  year={2023}
}
```

</details>

<details>
<summary><b>Example 3</b>: arXiv preprint upgraded to published version with title change (<a href="https://arxiv.org/abs/2211.03364v7">source</a>)</summary>

Before:
```bibtex
@article{khader2022medical,
  title={Medical Diffusion--Denoising Diffusion Probabilistic Models for 3D Medical Image Generation},
  author={Khader, Firas and Mueller-Franzes, Gustav and Arasteh, Soroosh Tayebi and Han, Tianyu and Haarburger, Christoph and Schulze-Hagen, Maximilian and Schad, Philipp and Engelhardt, Sandy and Baessler, Bettina and Foersch, Sebastian and others},
  journal={arXiv preprint arXiv:2211.03364},
  year={2022}
}
```

After:
```bibtex
% @article{khader2022medical,
%   title={Medical Diffusion--Denoising Diffusion Probabilistic Models for 3D Medical Image Generation},
%   author={Khader, Firas and Mueller-Franzes, Gustav and Arasteh, Soroosh Tayebi and Han, Tianyu and Haarburger, Christoph and Schulze-Hagen, Maximilian and Schad, Philipp and Engelhardt, Sandy and Baessler, Bettina and Foersch, Sebastian and others},
%   journal={arXiv preprint arXiv:2211.03364},
%   year={2022}
% }
% bibtidy: source https://doi.org/10.1038/s41598-023-34341-2
% bibtidy: updated from arXiv to published version (Scientific Reports 2023), title updated
@article{khader2022medical,
  title={Denoising Diffusion Probabilistic Models for 3D Medical Image Generation},
  author={Khader, Firas and Mueller-Franzes, Gustav and Arasteh, Soroosh Tayebi and Han, Tianyu and Haarburger, Christoph and Schulze-Hagen, Maximilian and Schad, Philipp and Engelhardt, Sandy and Baessler, Bettina and Foersch, Sebastian and others},
  journal={Scientific Reports},
  volume={13},
  year={2023}
}
```

</details>

<details>
<summary><b>Example 4</b>: Wrong page numbers corrected via CrossRef (<a href="https://scholar.googleusercontent.com/scholar.bib?q=info:IrnONgPsYfIJ:scholar.google.com/&output=citation&scisdr=Cjzimnz0ENylm3JE4bI:ADi0EEUAAAAAab9C+bLnAvK8D-XbsBF71_Icwng&scisig=ADi0EEUAAAAAab9C+TOLh0TDAOTbklme_5Hngoc&scisf=4&ct=citation&cd=-1&hl=en">source</a>)</summary>

Before:
```bibtex
@inproceedings{strudel2021segmenter,
  title={Segmenter: Transformer for semantic segmentation},
  author={Strudel, Robin and Garcia, Ricardo and Laptev, Ivan and Schmid, Cordelia},
  booktitle={Proceedings of the IEEE/CVF international conference on computer vision},
  pages={7262--7272},
  year={2021}
}
```

After:
```bibtex
% @inproceedings{strudel2021segmenter,
%   title={Segmenter: Transformer for semantic segmentation},
%   author={Strudel, Robin and Garcia, Ricardo and Laptev, Ivan and Schmid, Cordelia},
%   booktitle={Proceedings of the IEEE/CVF international conference on computer vision},
%   pages={7262--7272},
%   year={2021}
% }
% bibtidy: source https://doi.org/10.1109/iccv48922.2021.00717
% bibtidy: corrected page range 7262--7272 → 7242--7252
@inproceedings{strudel2021segmenter,
  title={Segmenter: Transformer for semantic segmentation},
  author={Strudel, Robin and Garcia, Ricardo and Laptev, Ivan and Schmid, Cordelia},
  booktitle={Proceedings of the IEEE/CVF international conference on computer vision},
  pages={7242--7252},
  year={2021}
}
```

</details>

<details>
<summary><b>Example 5</b>: bioRxiv preprint duplicated with published version</summary>

Before:
```bibtex
@article{watson2022broadly,
  title={Broadly applicable and accurate protein design by integrating structure prediction networks and diffusion generative models},
  author={Watson, Joseph L and Juergens, David and Bennett, Nathaniel R and Trippe, Brian L and Yim, Jason and Eisenach, Helen E and Ahern, Woody and Borst, Andrew J and Ragotte, Robert J and Milles, Lukas F and others},
  journal={BioRxiv},
  pages={2022--12},
  year={2022},
  publisher={Cold Spring Harbor Laboratory}
}

@article{watson2023novo,
  title={De novo design of protein structure and function with RFdiffusion},
  author={Watson, Joseph L and Juergens, David and Bennett, Nathaniel R and Trippe, Brian L and Yim, Jason and Eisenach, Helen E and Ahern, Woody and Borst, Andrew J and Ragotte, Robert J and Milles, Lukas F and others},
  journal={Nature},
  volume={620},
  pages={1089--1100},
  year={2023},
  publisher={Nature Publishing Group UK London}
}
```

After:
```bibtex
% bibtidy: DUPLICATE of watson2023novo — consider removing
@article{watson2022broadly,
  title={Broadly applicable and accurate protein design by integrating structure prediction networks and diffusion generative models},
  author={Watson, Joseph L and Juergens, David and Bennett, Nathaniel R and Trippe, Brian L and Yim, Jason and Eisenach, Helen E and Ahern, Woody and Borst, Andrew J and Ragotte, Robert J and Milles, Lukas F and others},
  journal={BioRxiv},
  pages={2022--12},
  year={2022},
  publisher={Cold Spring Harbor Laboratory}
}

@article{watson2023novo,
  title={De novo design of protein structure and function with RFdiffusion},
  author={Watson, Joseph L and Juergens, David and Bennett, Nathaniel R and Trippe, Brian L and Yim, Jason and Eisenach, Helen E and Ahern, Woody and Borst, Andrew J and Ragotte, Robert J and Milles, Lukas F and others},
  journal={Nature},
  volume={620},
  pages={1089--1100},
  year={2023},
  publisher={Nature Publishing Group UK London}
}
```

</details>

## FAQ

**Why are page numbers so often wrong?**

Page numbers are one of the most common errors in BibTeX entries. Google Scholar extracts metadata by scraping PDFs rather than querying publisher databases, so page numbers are frequently incorrect. Worse, even official sources can disagree — for example, the same CVPR 2020 paper "Momentum Contrast for Unsupervised Visual Representation Learning" has pages 9729--9738 on [CVF Open Access](https://openaccess.thecvf.com/content_CVPR_2020/html/He_Momentum_Contrast_for_Unsupervised_Visual_Representation_Learning_CVPR_2020_paper.html) but pages 9726--9735 on [IEEE Xplore](https://ieeexplore.ieee.org/document/9157636), because IEEE re-paginates when compiling the full proceedings volume. bibtidy uses CrossRef as the authoritative source for page numbers. CrossRef gets metadata directly from publishers via DOI registration, so for IEEE/CVF conferences it returns the IEEE Xplore pagination (9726--9735 in the example above). When sources conflict, bibtidy applies the DOI-linked version and flags the entry with `% bibtidy: REVIEW` so you can verify.

## License

MIT
