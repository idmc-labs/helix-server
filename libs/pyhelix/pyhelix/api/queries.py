class GraphqlQuery:
    # Queries
    me = {
        "operationName": "pyhelixMe",
        "query": """
          query pyhelixMe {
            me {
              id
              fullName
              isActive
            }
          }
         """,
    }

    # NOTE: Pagination not required
    violence_sub_types = {
        "operationName": "pyhelixViolenceSubTypes",
        "query": """
           query pyhelixViolenceSubTypes {
             violenceList {
               totalCount
               pageSize
               page
               results {
                 id
                 subTypes {
                   results {
                     id
                     name
                   }
                 }
               }
             }
           }
        """,
    }

    # NOTE: Pagination not required
    disaster_sub_types = {
        "operationName": "pyhelixDisasterSubTypes",
        "query": """
           query pyhelixDisasterSubTypes {
             disasterSubTypeList {
               totalCount
               pageSize
               page
               results {
                 id
                 name
               }
             }
           }
        """,
    }

    # NOTE: Pagination not required
    other_sub_types = {
        "operationName": "pyhelixOtherSubTypes",
        "query": """
           query pyhelixOtherSubTypes {
             otherSubTypeList {
               totalCount
               pageSize
               page
               results {
                 id
                 name
               }
             }
           }
        """,
    }

    @classmethod
    def figure_tags(cls, page: int, page_size: int = 100):
        return {
            "operationName": "pyhelixFigureTags",
            "query": """
                query pyhelixFigureTags($page: Int!, $pageSize: Int!) {
                  figureTagList(page: $page, pageSize: $pageSize) {
                    totalCount
                    pageSize
                    page
                    results {
                      id
                      name
                    }
                  }
                }
             """,
            "variables": {
                "page": page,
                "pageSize": page_size,
            },
        }

    @classmethod
    def organizations(cls, page: int, page_size: int = 100):
        return {
            "operationName": "pyhelixOrganizations",
            "query": """
                query pyhelixOrganizations($page: Int!, $pageSize: Int!) {
                  organizationList(page: $page, pageSize: $pageSize) {
                    totalCount
                    pageSize
                    page
                    results {
                      id
                      name
                    }
                  }
                }
             """,
            "variables": {
                "page": page,
                "pageSize": page_size,
            },
        }

    @classmethod
    def countries(cls, page: int, page_size: int = 100):
        return {
            "operationName": "pyhelixCountries",
            "query": """
                query pyhelixCountries($page: Int!, $pageSize: Int!) {
                  countryList(page: $page, pageSize: $pageSize) {
                    totalCount
                    pageSize
                    page
                    results {
                      id
                      name
                    }
                  }
                }
             """,
            "variables": {
                "page": page,
                "pageSize": page_size,
            },
        }

    # Mutations

    @classmethod
    def login(cls, email: str, password: str):
        return {
            "operationName": "pyhelixLogin",
            "query": """
              mutation pyhelixLogin($input: LoginInputType!) {
                login(data: $input) {
                  ok
                  captchaRequired
                  errors
                  result {
                    id
                    fullName
                    isActive
                  }
                }
              }
            """,
            "variables": {
                "input": {
                    "email": email,
                    "password": password,
                }
            },
        }
