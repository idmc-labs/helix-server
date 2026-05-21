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
    def users_by_email(cls, email: str):
        """
        Look up a user by exact email (case-insensitive) via
        ``UserFilter.email``. Helix masks ``UserType.email`` for non-self users
        so we can't read it back — we trust the filter and pick the single
        match.
        """
        return {
            "operationName": "pyhelixUsersByEmail",
            "query": """
                query pyhelixUsersByEmail($email: String!) {
                  users(page: 1, pageSize: 2, filters: {email: $email, includeInactive: false}) {
                    totalCount
                    results {
                      id
                      fullName
                      isActive
                    }
                  }
                }
             """,
            "variables": {
                "email": email,
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
                      iso2
                      iso3
                      idmcShortName
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
    def hulk_bulk_import(cls, id: str):
        """Read the current state (status + aggregate counts + dataset file URLs) of a HulkBulkImport."""
        return {
            "operationName": "pyhelixHulkBulkImport",
            "query": """
                query pyhelixHulkBulkImport($id: ID!) {
                  hulkBulkImport(id: $id) {
                    id
                    status
                    statusDisplay
                    successCount
                    failureCount
                    startedAt
                    completedAt
                    datasets {
                      id
                      importType
                      successCount
                      failureCount
                      importFile
                      successFile
                      failureFile
                    }
                  }
                }
             """,
            "variables": {"id": id},
        }

    # Mutations

    # Shape of the trigger_hulk_bulk_import mutation. The variables dict is
    # *only* the null-placeholder shape (a list of {importType, importFile:null}
    # objects) — the actual file objects ride on the multipart envelope,
    # see ``HelixClient.trigger_hulk_bulk_import``.
    trigger_hulk_bulk_import_query = """
        mutation pyhelixTriggerHulkBulkImport($data: HulkBulkImportCreateInputType!) {
          triggerHulkBulkImport(data: $data) {
            ok
            errors
            result {
              id
              status
            }
          }
        }
    """

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
