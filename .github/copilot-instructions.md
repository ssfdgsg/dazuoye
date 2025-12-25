# AI Agent Coding Guidelines for Movie Recommendation System

## Project Overview
This repository implements a movie recommendation system using a combination of Python, Scala, and SQL. The system includes components for data preprocessing, model training, and serving recommendations. It leverages Apache Spark for distributed data processing and machine learning tasks.

### Key Components
- **Python**: Contains scripts for recommendation logic and testing (e.g., `movie_recommender.py`).
- **Scala**: Implements data preprocessing and model training using Spark MLlib (e.g., `MoviePreprocess.scala`, `RecommendationModel.scala`).
- **SQL**: Defines database schemas and queries for managing movie-related data (e.g., `movie_tables.sql`).
- **Web**: A lightweight web application for serving recommendations (`app.py`).

## Developer Workflows

### Build and Run
1. **Start Hadoop**:
   ```bash
   ssh localhost
   cd ~/Desktop
   ./starthadoop.sh
   ```
2. **Run the System**:
   ```bash
   ./run.sh
   ```
   This script orchestrates the entire pipeline, including data loading, preprocessing, and model training.

### Testing
- **Python Tests**:
  ```bash
  ./scripts/testForModule/testPython.sh
  ```
- **Scala Tests**:
  ```bash
  ./scripts/testForModule/testJavaSparkSubmit.sh
  ```

### Debugging
- Use the `log4j.properties` file in the `conf/` directory to configure logging levels for debugging.
- Check `log.txt` for runtime logs.

## Project-Specific Conventions
- **Data Serialization**: Ensure compatibility between Python and Scala components by using little-endian byte order for serialized vectors.
- **Error Handling**: Catch and log all exceptions during data processing to prevent pipeline failures.
- **Code Style**:
  - Follow PEP 8 for Python.
  - Use Scala style conventions for Spark code.

## Integration Points
- **HDFS**: Stores raw, preprocessed, and feature-engineered data.
- **MySQL**: Manages metadata and user-specific recommendations.
- **Spark MLlib**: Provides algorithms for collaborative filtering and feature extraction.

## External Dependencies
- **Python**:
  - Install dependencies listed in `src/web/requirements.txt`:
    ```bash
    pip install -r src/web/requirements.txt
    ```
- **Scala**:
  - Managed via `pom.xml` (Maven).

## Examples
- **Running a Recommendation Query**:
  ```bash
  python3.8 code/python/movie_recommender.py --user_id 100 --topN 5
  ```
- **Preprocessing Data**:
  ```bash
  spark-submit --class com.movie.preprocess.MoviePreprocess target/scala-2.12/movie-recommendation-system_2.12-1.0.jar
  ```

## Notes
- Always validate data schemas before running Spark jobs.
- Ensure consistent versions of dependencies across Python and Scala components.

---

For further details, refer to the `README.md` and `run.sh` scripts.