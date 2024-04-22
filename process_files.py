import os
from bs4 import BeautifulSoup
import domolibrary_extensions.utils.convert as deuc
import re
from markdownify import markdownify as md
from urllib.parse import urljoin


def crawl_directory(file_path="./content"):
    file_ls = []
    for dirpath, _, filenames in os.walk(file_path):
        file_ls += [
            os.path.join(dirpath, file_name)
            for file_name in filenames
            if file_name == "index.html"
        ]

    return file_ls


def test_file_exists(file_path):
    if not os.path.exists(file_path):
        raise Exception(f"{file_path} does not exist")

    return True


def read_file(file_name):
    test_file_exists(file_name)

    with open(file_name, encoding="utf-8") as f:
        return f.read()


def extract_content_soup(path_name, debug_prn: bool = False):  # returns content_soup
    data = read_file(path_name)

    soup = BeautifulSoup(data, features="lxml")

    content_soup = soup.find(class_=["content"])
    # content_soup = soup

    if not content_soup:
        raise Exception(f"content not available in {path_name}.  Check the download.")

    return content_soup


def process_html_str(html):
    # remove image tags
    html = md(html, strip=["a", "img"])

    # clean up extra newlines
    html = "".join([line.rstrip() + "\n" for line in html.splitlines()])
    html = re.sub(r"(\n\n.?)+", r"\n\n", html)

    return html


def extract_url(file_path, base_url="https://domo-support.domo.com"):
    url = file_path.replace("_", "/")
    return urljoin(base_url, url).replace("/content", "").replace("/index.html", "")


def extract_title(soup, return_raw=False):
    title_soup = (
        soup.find(class_="page-header")
        and soup.find(class_="page-header").find_next("h1")
        or soup.find(class_="article-head")
    )

    if soup.find(class_="homePage_BrowseResources") and not title_soup:
        return "Home"

    if return_raw:
        return title_soup

    return title_soup.text.strip()


def extract_description(soup, return_raw: bool = False):
    description_soup = soup.find(class_="page-header-description")

    if return_raw:
        return description_soup

    return description_soup and description_soup.text.strip() or None


def extract_article(soup, return_raw=False):
    """article content is formed in slds-form.  extract and process metadata"""

    try:
        form_ls = soup.find_all(class_="slds-form")
        res = {
            deuc.convert_str_file_name(
                deuc.convert_str_to_snake_case(
                    ele.find(class_="slds-form-element__label").text
                ).strip()
            ): process_html_str(
                str(ele.find(class_="slds-form-element__control"))
            ).strip()
            for form in form_ls
            for ele in form.find_all(class_="slds-form-element")
        }

        page_content = res.pop("article_body")

        res = {
            key: value
            for key, value in res.items()
            if key
            not in [
                "preview_article",
                "summarybriefly_describe_the_article_the_summary_is_used_in_search_results_to_help_users_find_relevant_articles_you_can_improve_the_accuracy_of_search_results_by_including_phrases_that_your_customers_use_to_describe_this_issue_or_topic",
                "primary_version",
                "",
                "article_created_date",
            ]
            and (value and value != "")
        }

        res["url"] = f"https://domo-support.domo.com/s/article/{res.pop('url_name')}"
        res["article_total_view_count"] = int(
            res["article_total_view_count"].replace(",", "")
        )
        res["first_published_date"] = deuc.convert_str_to_date(
            res["first_published_date"]
        ).strftime("%Y-%m-%d")

        description = extract_description(soup)
        if description:
            res["description"] = description

        res = {
            "page_content": page_content,
            "metadata": {
                **res,
                "title": extract_title(soup=soup),
            },
        }

        return res

    except Exception as e:
        print(e)
        return None
