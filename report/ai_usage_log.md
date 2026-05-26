# AI Usage Log

I used ChatGPT as a debugging assistant during this assignment. I mainly used it to help plan the project folder structure, and think through possible approaches for handling very large parquet files.

During development, I first tried a pandas-based pipeline, but it was not practical for the full bus-level dataset because the files were too large for my local environment. I then used AI assistance to debug the memory and environment issues and redesigned the workflow into a lightweight PyArrow-based batch processing pipeline.

My own work included downloading and organizing the data files, running the code locally, checking file paths, testing the quick and full pipeline modes, verifying the forecast output schema, checking the generated metrics, and reviewing the final report. I also checked that the forecast files contained the required columns and that the output files were generated correctly.

AI assistance was used for:

- understanding the assignment instructions
- planning the project structure
- debugging Python environment issues
- redesigning the pipeline to avoid memory problems
- drafting and improving the summary report
- checking whether the output schema matched the assignment requirements

The final code, output files, evaluation metrics, and report were reviewed and validated by me before submission.