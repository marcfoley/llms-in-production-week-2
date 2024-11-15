import time

import guardrails as gd
import openai
import streamlit as st

from src.cached_resources import (
    get_exact_match_cache,         # ADD IMPORT 
    get_guard,
    get_semantic_cache,            # ADD IMPORT
    instrument,
)
from src.constants import OPENAI_MODEL_ARGUMENTS
from src.models import LLMResponse

st.set_page_config(page_title="SQL Code Generator")
st.title("SQL Code Generator")

def generate_response(
    input_text: str,
    cache,
    guard: gd.Guard,
    distance_threshold: float | None,
    cache_strategy: str,
) -> None:
    """
    Generate a response for the given input text, taking in the cache and guard.
    This function checks the cache for similar responses, and if none are found, it queries the LLM.
    """
    try:
        start_time = time.time()

        if cache_strategy == "Semantic Cache":
            # Check the semantic cache for a semantically similar entry with the selected distance threshold
            cached_result = cache.check(
                prompt=input_text, distance_threshold=distance_threshold
            )
        else:
            # Check the exact match cache using a simple Redis Hash lookup
            cached_result = cache.get(input_text)
            if cached_result:
                cached_result = [{"response": cached_result.decode("utf-8")}]

        # If no cached result is found (cache miss)
        if not cached_result:
            (
                _,
                validated_response,
                _,
                validation_passed,
                error,
            ) = guard(
                openai.chat.completions.create,
                prompt_params={
                    "query": input_text,
                },
                **OPENAI_MODEL_ARGUMENTS,
            )
            total_time = time.time() - start_time

            # Handle errors or invalid responses
            if error or not validation_passed or not validated_response:
                st.error(f"Unable to produce an answer due to: {error}")
            else:
                valid_sql = LLMResponse(**validated_response)
                generated_sql = valid_sql.generated_sql
                st.info(generated_sql)
                st.info(f"That query took: {total_time:.2f}s")

                # Store the result in the appropriate cache for future use
                if cache_strategy == "Semantic Cache":
                    cache.store(
                        prompt=input_text,
                        response=generated_sql,
                        # Metadata to track when the response was generated
                        metadata={"generated_at": time.time()},
                    )
                else:
                    cache.set(input_text, generated_sql)

        # If a cached result is found (cache hit)
        else:
            total_time = (
                time.time() - start_time
            )  # Calculate the total time taken to retrieve from cache
            st.info(cached_result[0]["response"])  # Display the cached response
            st.info(f"That query took: {total_time:.2f}s")  # Display the time taken
    except Exception as e:
        st.error(f"Error: {e}")  # Display any errors that occur during the process

def main():
    cache_strategy = st.radio(
        "Select cache strategy:", ("Exact Match Cache", "Semantic Cache")
    )

    if cache_strategy == "Semantic Cache":
        distance_threshold = st.slider(
            "Select distance threshold for semantic cache:",
            min_value=0.0,
            max_value=1.0,
            value=0.1,
            step=0.01,
        )
    else:
        distance_threshold = None

    guard = get_guard()
    cache = (
        get_semantic_cache()
        if cache_strategy == "Semantic Cache"
        else get_exact_match_cache()
    )  # Initialize cache based on strategy
    instrument()

    with st.form("my_form"):
        st.warning(
            "Our models can make mistakes!", icon="🚨"
        )  # Warning message for users
        text = st.text_area("Enter text:")  # Text input area for the query
        submitted = st.form_submit_button("Submit")  # Button to submit the form
        if submitted:
            # Generate response for the input text using the selected cache strategy and guard
            generate_response(text, cache, guard, distance_threshold, cache_strategy)


if __name__ == "__main__":
    main()
