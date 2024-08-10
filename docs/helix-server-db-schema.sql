--
-- PostgreSQL database dump
--

-- Dumped from database version 13.15 (Debian 13.15-1.pgdg120+1)
-- Dumped by pg_dump version 14.13 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: unaccent; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public;


--
-- Name: EXTENSION unaccent; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION unaccent IS 'text search dictionary that removes accents';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.auth_group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.auth_group_id_seq OWNED BY public.auth_group.id;


--
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_group_permissions (
    id integer NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.auth_group_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.auth_group_permissions_id_seq OWNED BY public.auth_group_permissions.id;


--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.auth_permission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.auth_permission_id_seq OWNED BY public.auth_permission.id;


--
-- Name: authtoken_token; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.authtoken_token (
    key character varying(40) NOT NULL,
    created timestamp with time zone NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: contact_communication; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contact_communication (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    subject character varying(512) NOT NULL,
    content text NOT NULL,
    medium_id integer,
    contact_id integer NOT NULL,
    created_by_id integer,
    last_modified_by_id integer,
    old_id character varying(32),
    attachment_id integer,
    country_id integer,
    date date
);


--
-- Name: contact_communication_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contact_communication_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contact_communication_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contact_communication_id_seq OWNED BY public.contact_communication.id;


--
-- Name: contact_communicationmedium; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contact_communicationmedium (
    id integer NOT NULL,
    name character varying(256) NOT NULL
);


--
-- Name: contact_communicationmedium_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contact_communicationmedium_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contact_communicationmedium_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contact_communicationmedium_id_seq OWNED BY public.contact_communicationmedium.id;


--
-- Name: contact_contact; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contact_contact (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    designation integer NOT NULL,
    first_name character varying(256) NOT NULL,
    last_name character varying(256) NOT NULL,
    gender integer NOT NULL,
    job_title character varying(256) NOT NULL,
    email character varying(254),
    phone character varying(256),
    comment text,
    country_id integer,
    created_by_id integer,
    last_modified_by_id integer,
    organization_id integer,
    old_id character varying(32),
    skype character varying(32),
    full_name character varying(512)
);


--
-- Name: contact_contact_countries_of_operation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contact_contact_countries_of_operation (
    id integer NOT NULL,
    contact_id integer NOT NULL,
    country_id integer NOT NULL
);


--
-- Name: contact_contact_countries_of_operation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contact_contact_countries_of_operation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contact_contact_countries_of_operation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contact_contact_countries_of_operation_id_seq OWNED BY public.contact_contact_countries_of_operation.id;


--
-- Name: contact_contact_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contact_contact_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contact_contact_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contact_contact_id_seq OWNED BY public.contact_contact.id;


--
-- Name: contextualupdate_contextualupdate; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contextualupdate_contextualupdate (
    id integer NOT NULL,
    old_id character varying(32),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    url character varying(2000),
    article_title text NOT NULL,
    publish_date timestamp with time zone,
    source_excerpt text,
    idmc_analysis text,
    is_confidential boolean NOT NULL,
    crisis_types integer[],
    created_by_id integer,
    document_id integer,
    last_modified_by_id integer,
    preview_id integer,
    caveats text,
    excerpt_idu text
);


--
-- Name: contextualupdate_contextualupdate_countries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contextualupdate_contextualupdate_countries (
    id integer NOT NULL,
    contextualupdate_id integer NOT NULL,
    country_id integer NOT NULL
);


--
-- Name: contextualupdate_contextualupdate_countries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contextualupdate_contextualupdate_countries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contextualupdate_contextualupdate_countries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contextualupdate_contextualupdate_countries_id_seq OWNED BY public.contextualupdate_contextualupdate_countries.id;


--
-- Name: contextualupdate_contextualupdate_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contextualupdate_contextualupdate_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contextualupdate_contextualupdate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contextualupdate_contextualupdate_id_seq OWNED BY public.contextualupdate_contextualupdate.id;


--
-- Name: contextualupdate_contextualupdate_publishers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contextualupdate_contextualupdate_publishers (
    id integer NOT NULL,
    contextualupdate_id integer NOT NULL,
    organization_id integer NOT NULL
);


--
-- Name: contextualupdate_contextualupdate_publishers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contextualupdate_contextualupdate_publishers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contextualupdate_contextualupdate_publishers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contextualupdate_contextualupdate_publishers_id_seq OWNED BY public.contextualupdate_contextualupdate_publishers.id;


--
-- Name: contextualupdate_contextualupdate_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contextualupdate_contextualupdate_sources (
    id integer NOT NULL,
    contextualupdate_id integer NOT NULL,
    organization_id integer NOT NULL
);


--
-- Name: contextualupdate_contextualupdate_sources_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contextualupdate_contextualupdate_sources_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contextualupdate_contextualupdate_sources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contextualupdate_contextualupdate_sources_id_seq OWNED BY public.contextualupdate_contextualupdate_sources.id;


--
-- Name: contextualupdate_contextualupdate_tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contextualupdate_contextualupdate_tags (
    id integer NOT NULL,
    contextualupdate_id integer NOT NULL,
    figuretag_id integer NOT NULL
);


--
-- Name: contextualupdate_contextualupdate_tags_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contextualupdate_contextualupdate_tags_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contextualupdate_contextualupdate_tags_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contextualupdate_contextualupdate_tags_id_seq OWNED BY public.contextualupdate_contextualupdate_tags.id;


--
-- Name: contrib_attachment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contrib_attachment (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    attachment character varying(2000) NOT NULL,
    attachment_for integer,
    created_by_id integer,
    last_modified_by_id integer,
    encoding character varying(256),
    filetype_detail character varying(2000),
    mimetype character varying(256)
);


--
-- Name: contrib_attachment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contrib_attachment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contrib_attachment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contrib_attachment_id_seq OWNED BY public.contrib_attachment.id;


--
-- Name: contrib_bulkapioperation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contrib_bulkapioperation (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    action integer NOT NULL,
    filters jsonb,
    payload jsonb,
    status integer NOT NULL,
    success_count integer,
    failure_count integer,
    created_by_id integer NOT NULL,
    completed_at timestamp with time zone,
    failure_list jsonb NOT NULL,
    snapshot character varying(2000),
    started_at timestamp with time zone,
    success_list jsonb NOT NULL,
    CONSTRAINT contrib_bulkapioperation_failure_count_check CHECK ((failure_count >= 0)),
    CONSTRAINT contrib_bulkapioperation_success_count_check CHECK ((success_count >= 0))
);


--
-- Name: contrib_bulkapioperation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contrib_bulkapioperation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contrib_bulkapioperation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contrib_bulkapioperation_id_seq OWNED BY public.contrib_bulkapioperation.id;


--
-- Name: contrib_client; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contrib_client (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    name character varying(255) NOT NULL,
    code character varying(100) NOT NULL,
    created_by_id integer,
    last_modified_by_id integer,
    is_active boolean NOT NULL,
    acronym character varying(255),
    contact_email character varying(254),
    contact_name character varying(255),
    contact_website character varying(200),
    opted_out_of_emails boolean NOT NULL,
    other_notes character varying(255),
    use_cases integer[] NOT NULL
);


--
-- Name: contrib_client_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contrib_client_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contrib_client_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contrib_client_id_seq OWNED BY public.contrib_client.id;


--
-- Name: contrib_clienttrackinfo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contrib_clienttrackinfo (
    id integer NOT NULL,
    api_type character varying(40) NOT NULL,
    requests_per_day integer NOT NULL,
    tracked_date date NOT NULL,
    client_id integer NOT NULL
);


--
-- Name: contrib_clienttrackinfo_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contrib_clienttrackinfo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contrib_clienttrackinfo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contrib_clienttrackinfo_id_seq OWNED BY public.contrib_clienttrackinfo.id;


--
-- Name: contrib_exceldownload; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contrib_exceldownload (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    download_type integer NOT NULL,
    status integer NOT NULL,
    file character varying(2000),
    filters jsonb,
    created_by_id integer,
    last_modified_by_id integer,
    file_size integer
);


--
-- Name: contrib_exceldownload_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contrib_exceldownload_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contrib_exceldownload_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contrib_exceldownload_id_seq OWNED BY public.contrib_exceldownload.id;


--
-- Name: contrib_sourcepreview; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contrib_sourcepreview (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    url character varying(2000) NOT NULL,
    token character varying(64),
    pdf character varying(2000),
    created_by_id integer,
    last_modified_by_id integer,
    remark text,
    status integer NOT NULL
);


--
-- Name: contrib_sourcepreview_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contrib_sourcepreview_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contrib_sourcepreview_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contrib_sourcepreview_id_seq OWNED BY public.contrib_sourcepreview.id;


--
-- Name: country_contextualanalysis; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.country_contextualanalysis (
    id integer NOT NULL,
    old_id character varying(32),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    update text NOT NULL,
    publish_date date,
    crisis_type integer,
    country_id integer NOT NULL,
    created_by_id integer,
    last_modified_by_id integer
);


--
-- Name: country_contextualanalysis_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.country_contextualanalysis_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: country_contextualanalysis_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.country_contextualanalysis_id_seq OWNED BY public.country_contextualanalysis.id;


--
-- Name: country_country; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.country_country (
    id integer NOT NULL,
    name character varying(256) NOT NULL,
    region_id integer NOT NULL,
    bounding_box double precision[],
    centroid double precision[],
    country_code smallint,
    idmc_full_name character varying(256),
    idmc_short_name character varying(256) NOT NULL,
    idmc_short_name_ar character varying(256),
    idmc_short_name_es character varying(256),
    idmc_short_name_fr character varying(256),
    iso3 character varying(5),
    geographical_group_id integer,
    iso2 character varying(4),
    monitoring_sub_region_id integer,
    sub_region_id integer,
    CONSTRAINT country_country_country_code_check CHECK ((country_code >= 0))
);


--
-- Name: country_country_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.country_country_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: country_country_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.country_country_id_seq OWNED BY public.country_country.id;


--
-- Name: country_countrypopulation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.country_countrypopulation (
    id integer NOT NULL,
    population integer NOT NULL,
    year integer NOT NULL,
    country_id integer NOT NULL,
    CONSTRAINT country_countrypopulation_population_check CHECK ((population >= 0)),
    CONSTRAINT country_countrypopulation_year_check CHECK ((year >= 0))
);


--
-- Name: country_countrypopulation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.country_countrypopulation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: country_countrypopulation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.country_countrypopulation_id_seq OWNED BY public.country_countrypopulation.id;


--
-- Name: country_countryregion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.country_countryregion (
    id integer NOT NULL,
    name character varying(256) NOT NULL
);


--
-- Name: country_countryregion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.country_countryregion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: country_countryregion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.country_countryregion_id_seq OWNED BY public.country_countryregion.id;


--
-- Name: country_countrysubregion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.country_countrysubregion (
    id integer NOT NULL,
    name character varying(256) NOT NULL
);


--
-- Name: country_countrysubregion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.country_countrysubregion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: country_countrysubregion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.country_countrysubregion_id_seq OWNED BY public.country_countrysubregion.id;


--
-- Name: country_geographicalgroup; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.country_geographicalgroup (
    id integer NOT NULL,
    name character varying(256) NOT NULL
);


--
-- Name: country_geographicalgroup_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.country_geographicalgroup_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: country_geographicalgroup_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.country_geographicalgroup_id_seq OWNED BY public.country_geographicalgroup.id;


--
-- Name: country_householdsize; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.country_householdsize (
    id integer NOT NULL,
    old_id character varying(32),
    year smallint NOT NULL,
    size double precision NOT NULL,
    country_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    created_by_id integer,
    data_source_category character varying(255) NOT NULL,
    is_active boolean NOT NULL,
    last_modified_by_id integer,
    modified_at timestamp with time zone NOT NULL,
    notes text,
    source character varying(255) NOT NULL,
    source_link character varying(255) NOT NULL,
    version_id character varying(16),
    CONSTRAINT country_householdsize_year_check CHECK ((year >= 0))
);


--
-- Name: country_householdsize_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.country_householdsize_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: country_householdsize_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.country_householdsize_id_seq OWNED BY public.country_householdsize.id;


--
-- Name: country_monitoringsubregion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.country_monitoringsubregion (
    id integer NOT NULL,
    name character varying(256) NOT NULL
);


--
-- Name: country_monitoringsubregion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.country_monitoringsubregion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: country_monitoringsubregion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.country_monitoringsubregion_id_seq OWNED BY public.country_monitoringsubregion.id;


--
-- Name: country_summary; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.country_summary (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    summary text NOT NULL,
    country_id integer NOT NULL,
    created_by_id integer,
    last_modified_by_id integer,
    old_id character varying(32)
);


--
-- Name: country_summary_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.country_summary_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: country_summary_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.country_summary_id_seq OWNED BY public.country_summary.id;


--
-- Name: crisis_crisis; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.crisis_crisis (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    name character varying(256) NOT NULL,
    crisis_type integer NOT NULL,
    crisis_narrative text NOT NULL,
    created_by_id integer,
    last_modified_by_id integer,
    end_date date,
    start_date date,
    end_date_accuracy integer,
    start_date_accuracy integer
);


--
-- Name: crisis_crisis_countries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.crisis_crisis_countries (
    id integer NOT NULL,
    crisis_id integer NOT NULL,
    country_id integer NOT NULL
);


--
-- Name: crisis_crisis_countries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.crisis_crisis_countries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: crisis_crisis_countries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.crisis_crisis_countries_id_seq OWNED BY public.crisis_crisis_countries.id;


--
-- Name: crisis_crisis_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.crisis_crisis_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: crisis_crisis_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.crisis_crisis_id_seq OWNED BY public.crisis_crisis.id;


--
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id integer NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.django_admin_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.django_admin_log_id_seq OWNED BY public.django_admin_log.id;


--
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.django_content_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: django_content_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.django_content_type_id_seq OWNED BY public.django_content_type.id;


--
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_migrations (
    id integer NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.django_migrations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: django_migrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.django_migrations_id_seq OWNED BY public.django_migrations.id;


--
-- Name: entry_disaggregatedage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entry_disaggregatedage (
    id integer NOT NULL,
    sex integer NOT NULL,
    uuid uuid NOT NULL,
    value integer,
    age_from integer,
    age_to integer,
    CONSTRAINT entry_disaggregatedage_age_from_check CHECK ((age_from >= 0)),
    CONSTRAINT entry_disaggregatedage_age_to_check CHECK ((age_to >= 0)),
    CONSTRAINT entry_disaggregatedage_value_check CHECK ((value >= 0))
);


--
-- Name: entry_disaggregatedage_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entry_disaggregatedage_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entry_disaggregatedage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entry_disaggregatedage_id_seq OWNED BY public.entry_disaggregatedage.id;


--
-- Name: entry_entry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entry_entry (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    url character varying(2000),
    article_title text NOT NULL,
    publish_date date NOT NULL,
    idmc_analysis text,
    created_by_id integer,
    last_modified_by_id integer,
    preview_id integer,
    document_id integer,
    is_confidential boolean NOT NULL,
    old_id character varying(32),
    associated_parked_item_id integer,
    review_status integer,
    document_url character varying(2000)
);


--
-- Name: entry_entry_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entry_entry_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entry_entry_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entry_entry_id_seq OWNED BY public.entry_entry.id;


--
-- Name: entry_entry_publishers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entry_entry_publishers (
    id integer NOT NULL,
    entry_id integer NOT NULL,
    organization_id integer NOT NULL
);


--
-- Name: entry_entry_publishers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entry_entry_publishers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entry_entry_publishers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entry_entry_publishers_id_seq OWNED BY public.entry_entry_publishers.id;


--
-- Name: entry_entryreviewer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entry_entryreviewer (
    id integer NOT NULL,
    status integer NOT NULL,
    entry_id integer NOT NULL,
    reviewer_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    created_by_id integer,
    last_modified_by_id integer,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16)
);


--
-- Name: entry_entryreviewer_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entry_entryreviewer_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entry_entryreviewer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entry_entryreviewer_id_seq OWNED BY public.entry_entryreviewer.id;


--
-- Name: entry_externalapidump; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entry_externalapidump (
    id integer NOT NULL,
    dump_file character varying(100),
    api_type character varying(40) NOT NULL,
    status integer NOT NULL
);


--
-- Name: entry_externalapidump_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entry_externalapidump_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entry_externalapidump_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entry_externalapidump_id_seq OWNED BY public.entry_externalapidump.id;


--
-- Name: entry_figure; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entry_figure (
    id integer NOT NULL,
    uuid uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    quantifier integer NOT NULL,
    reported integer NOT NULL,
    unit integer NOT NULL,
    household_size double precision,
    total_figures integer NOT NULL,
    role integer NOT NULL,
    start_date date,
    include_idu boolean NOT NULL,
    excerpt_idu text,
    is_disaggregated boolean NOT NULL,
    disaggregation_displacement_urban integer,
    disaggregation_displacement_rural integer,
    disaggregation_location_camp integer,
    disaggregation_location_non_camp integer,
    disaggregation_sex_male integer,
    disaggregation_sex_female integer,
    disaggregation_strata_json jsonb[],
    disaggregation_conflict integer,
    disaggregation_conflict_political integer,
    disaggregation_conflict_criminal integer,
    disaggregation_conflict_communal integer,
    disaggregation_conflict_other integer,
    created_by_id integer,
    entry_id integer NOT NULL,
    last_modified_by_id integer,
    country_id integer,
    end_date date,
    old_id character varying(32),
    category integer,
    is_housing_destruction boolean,
    was_subfact boolean NOT NULL,
    end_date_accuracy integer,
    start_date_accuracy integer,
    term integer,
    displacement_occurred integer,
    disaggregation_disability integer,
    disaggregation_indigenous_people integer,
    disaggregation_lgbtiq integer,
    calculation_logic text,
    source_excerpt text,
    event_id integer NOT NULL,
    disaster_category_id integer,
    disaster_sub_category_id integer,
    disaster_sub_type_id integer,
    disaster_type_id integer,
    figure_cause integer NOT NULL,
    osv_sub_type_id integer,
    violence_id integer,
    violence_sub_type_id integer,
    other_sub_type_id integer,
    approved_by_id integer,
    approved_on timestamp with time zone,
    review_status integer NOT NULL,
    CONSTRAINT entry_figure_disaggregation_conflict_communal_b0a61867_check CHECK ((disaggregation_conflict_communal >= 0)),
    CONSTRAINT entry_figure_disaggregation_conflict_criminal_8ac5ddcd_check CHECK ((disaggregation_conflict_criminal >= 0)),
    CONSTRAINT entry_figure_disaggregation_conflict_e96fbf3e_check CHECK ((disaggregation_conflict >= 0)),
    CONSTRAINT entry_figure_disaggregation_conflict_other_33e03d7e_check CHECK ((disaggregation_conflict_other >= 0)),
    CONSTRAINT entry_figure_disaggregation_conflict_political_dc4ae59b_check CHECK ((disaggregation_conflict_political >= 0)),
    CONSTRAINT entry_figure_disaggregation_disability_check CHECK ((disaggregation_disability >= 0)),
    CONSTRAINT entry_figure_disaggregation_displacement_rural_9f10bacf_check CHECK ((disaggregation_displacement_rural >= 0)),
    CONSTRAINT entry_figure_disaggregation_displacement_urban_ce7dc9e0_check CHECK ((disaggregation_displacement_urban >= 0)),
    CONSTRAINT entry_figure_disaggregation_indigenous_people_check CHECK ((disaggregation_indigenous_people >= 0)),
    CONSTRAINT entry_figure_disaggregation_lgbtiq_check CHECK ((disaggregation_lgbtiq >= 0)),
    CONSTRAINT entry_figure_disaggregation_location_camp_fb81736a_check CHECK ((disaggregation_location_camp >= 0)),
    CONSTRAINT entry_figure_disaggregation_location_non_camp_8200843e_check CHECK ((disaggregation_location_non_camp >= 0)),
    CONSTRAINT entry_figure_disaggregation_sex_female_1681d7e4_check CHECK ((disaggregation_sex_female >= 0)),
    CONSTRAINT entry_figure_disaggregation_sex_male_86c5af12_check CHECK ((disaggregation_sex_male >= 0)),
    CONSTRAINT entry_figure_reported_check CHECK ((reported >= 0)),
    CONSTRAINT entry_figure_total_figures_check CHECK ((total_figures >= 0))
);


--
-- Name: entry_figure_context_of_violence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entry_figure_context_of_violence (
    id integer NOT NULL,
    figure_id integer NOT NULL,
    contextofviolence_id integer NOT NULL
);


--
-- Name: entry_figure_context_of_violence_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entry_figure_context_of_violence_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entry_figure_context_of_violence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entry_figure_context_of_violence_id_seq OWNED BY public.entry_figure_context_of_violence.id;


--
-- Name: entry_figure_disaggregation_age; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entry_figure_disaggregation_age (
    id integer NOT NULL,
    figure_id integer NOT NULL,
    disaggregatedage_id integer NOT NULL
);


--
-- Name: entry_figure_disaggregation_age_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entry_figure_disaggregation_age_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entry_figure_disaggregation_age_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entry_figure_disaggregation_age_id_seq OWNED BY public.entry_figure_disaggregation_age.id;


--
-- Name: entry_figure_geo_locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entry_figure_geo_locations (
    id integer NOT NULL,
    figure_id integer NOT NULL,
    osmname_id integer NOT NULL
);


--
-- Name: entry_figure_geo_locations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entry_figure_geo_locations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entry_figure_geo_locations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entry_figure_geo_locations_id_seq OWNED BY public.entry_figure_geo_locations.id;


--
-- Name: entry_figure_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entry_figure_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entry_figure_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entry_figure_id_seq OWNED BY public.entry_figure.id;


--
-- Name: entry_figure_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entry_figure_sources (
    id integer NOT NULL,
    figure_id integer NOT NULL,
    organization_id integer NOT NULL
);


--
-- Name: entry_figure_sources_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entry_figure_sources_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entry_figure_sources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entry_figure_sources_id_seq OWNED BY public.entry_figure_sources.id;


--
-- Name: entry_figure_tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entry_figure_tags (
    id integer NOT NULL,
    figure_id integer NOT NULL,
    figuretag_id integer NOT NULL
);


--
-- Name: entry_figure_tags_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entry_figure_tags_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entry_figure_tags_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entry_figure_tags_id_seq OWNED BY public.entry_figure_tags.id;


--
-- Name: entry_figuretag; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entry_figuretag (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    name character varying(256) NOT NULL,
    created_by_id integer,
    last_modified_by_id integer
);


--
-- Name: entry_figuretag_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entry_figuretag_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entry_figuretag_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entry_figuretag_id_seq OWNED BY public.entry_figuretag.id;


--
-- Name: entry_osmname; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entry_osmname (
    id integer NOT NULL,
    uuid uuid NOT NULL,
    wikipedia text,
    rank integer,
    country text NOT NULL,
    country_code character varying(8),
    street text,
    wiki_data text,
    osm_id character varying(256) NOT NULL,
    osm_type character varying(256) NOT NULL,
    house_numbers text,
    identifier integer NOT NULL,
    city character varying(256),
    display_name character varying(512) NOT NULL,
    lon double precision NOT NULL,
    lat double precision NOT NULL,
    state text,
    bounding_box double precision[],
    type text,
    importance double precision,
    class_name text,
    name text NOT NULL,
    name_suffix text,
    place_rank integer,
    alternative_names text,
    accuracy integer NOT NULL,
    moved boolean NOT NULL
);


--
-- Name: entry_osmname_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entry_osmname_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entry_osmname_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entry_osmname_id_seq OWNED BY public.entry_osmname.id;


--
-- Name: event_actor; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_actor (
    id integer NOT NULL,
    name character varying(256) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    created_by_id integer,
    last_modified_by_id integer,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    country_id integer,
    torg character varying(10)
);


--
-- Name: event_actor_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_actor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_actor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_actor_id_seq OWNED BY public.event_actor.id;


--
-- Name: event_contextofviolence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_contextofviolence (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    name character varying(256) NOT NULL,
    created_by_id integer,
    last_modified_by_id integer
);


--
-- Name: event_contextofviolence_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_contextofviolence_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_contextofviolence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_contextofviolence_id_seq OWNED BY public.event_contextofviolence.id;


--
-- Name: event_disastercategory; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_disastercategory (
    id integer NOT NULL,
    name character varying(256) NOT NULL
);


--
-- Name: event_disastercategory_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_disastercategory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_disastercategory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_disastercategory_id_seq OWNED BY public.event_disastercategory.id;


--
-- Name: event_disastersubcategory; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_disastersubcategory (
    id integer NOT NULL,
    name character varying(256) NOT NULL,
    category_id integer NOT NULL
);


--
-- Name: event_disastersubcategory_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_disastersubcategory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_disastersubcategory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_disastersubcategory_id_seq OWNED BY public.event_disastersubcategory.id;


--
-- Name: event_disastersubtype; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_disastersubtype (
    id integer NOT NULL,
    name character varying(256) NOT NULL,
    type_id integer NOT NULL
);


--
-- Name: event_disastersubtype_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_disastersubtype_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_disastersubtype_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_disastersubtype_id_seq OWNED BY public.event_disastersubtype.id;


--
-- Name: event_disastertype; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_disastertype (
    id integer NOT NULL,
    name character varying(256) NOT NULL,
    disaster_sub_category_id integer NOT NULL
);


--
-- Name: event_disastertype_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_disastertype_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_disastertype_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_disastertype_id_seq OWNED BY public.event_disastertype.id;


--
-- Name: event_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_event (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    name character varying(256) NOT NULL,
    event_type integer NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    event_narrative text,
    actor_id integer,
    created_by_id integer,
    crisis_id integer,
    disaster_category_id integer,
    disaster_sub_category_id integer,
    disaster_sub_type_id integer,
    disaster_type_id integer,
    last_modified_by_id integer,
    violence_id integer,
    violence_sub_type_id integer,
    old_id character varying(32),
    end_date_accuracy integer,
    start_date_accuracy integer,
    glide_numbers character varying(256)[],
    osv_sub_type_id integer,
    ignore_qa boolean NOT NULL,
    other_sub_type_id integer,
    assigned_at timestamp with time zone,
    assignee_id integer,
    assigner_id integer,
    review_status integer NOT NULL,
    include_triangulation_in_qa boolean NOT NULL
);


--
-- Name: event_event_context_of_violence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_event_context_of_violence (
    id integer NOT NULL,
    event_id integer NOT NULL,
    contextofviolence_id integer NOT NULL
);


--
-- Name: event_event_context_of_violence_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_event_context_of_violence_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_event_context_of_violence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_event_context_of_violence_id_seq OWNED BY public.event_event_context_of_violence.id;


--
-- Name: event_event_countries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_event_countries (
    id integer NOT NULL,
    event_id integer NOT NULL,
    country_id integer NOT NULL
);


--
-- Name: event_event_countries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_event_countries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_event_countries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_event_countries_id_seq OWNED BY public.event_event_countries.id;


--
-- Name: event_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_event_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_event_id_seq OWNED BY public.event_event.id;


--
-- Name: event_eventcode; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_eventcode (
    id integer NOT NULL,
    uuid uuid NOT NULL,
    event_code_type integer NOT NULL,
    event_code character varying(256) NOT NULL,
    country_id integer NOT NULL,
    event_id integer NOT NULL
);


--
-- Name: event_eventcode_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_eventcode_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_eventcode_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_eventcode_id_seq OWNED BY public.event_eventcode.id;


--
-- Name: event_osvsubtype; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_osvsubtype (
    id integer NOT NULL,
    name character varying(256) NOT NULL
);


--
-- Name: event_osvsubtype_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_osvsubtype_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_osvsubtype_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_osvsubtype_id_seq OWNED BY public.event_osvsubtype.id;


--
-- Name: event_othersubtype; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_othersubtype (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    name character varying(256) NOT NULL,
    created_by_id integer,
    last_modified_by_id integer
);


--
-- Name: event_othersubtype_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_othersubtype_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_othersubtype_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_othersubtype_id_seq OWNED BY public.event_othersubtype.id;


--
-- Name: event_violence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_violence (
    id integer NOT NULL,
    name character varying(256) NOT NULL
);


--
-- Name: event_violence_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_violence_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_violence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_violence_id_seq OWNED BY public.event_violence.id;


--
-- Name: event_violencesubtype; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_violencesubtype (
    id integer NOT NULL,
    name character varying(256) NOT NULL,
    violence_id integer NOT NULL
);


--
-- Name: event_violencesubtype_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_violencesubtype_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_violencesubtype_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_violencesubtype_id_seq OWNED BY public.event_violencesubtype.id;


--
-- Name: extraction_extractionquery; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    filter_figure_start_after date,
    filter_figure_end_before date,
    filter_figure_roles integer[],
    created_by_id integer,
    last_modified_by_id integer,
    name character varying(128) NOT NULL,
    filter_entry_article_title text,
    filter_figure_crisis_types integer[],
    filter_figure_glide_number character varying(100)[],
    filter_figure_displacement_types integer[],
    filter_figure_category_types character varying(8)[],
    filter_figure_has_disaggregated_data boolean,
    filter_figure_categories integer[],
    filter_figure_terms integer[],
    filter_figure_review_status integer[],
    filter_is_figure_to_be_reviewed boolean
);


--
-- Name: extraction_extractionquery_filter_context_of_violence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery_filter_context_of_violence (
    id integer NOT NULL,
    extractionquery_id integer NOT NULL,
    contextofviolence_id integer NOT NULL
);


--
-- Name: extraction_extractionquery_filter_context_of_violence_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_filter_context_of_violence_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_filter_context_of_violence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_filter_context_of_violence_id_seq OWNED BY public.extraction_extractionquery_filter_context_of_violence.id;


--
-- Name: extraction_extractionquery_filter_created_by; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery_filter_created_by (
    id integer NOT NULL,
    extractionquery_id integer NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: extraction_extractionquery_filter_entry_created_by_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_filter_entry_created_by_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_filter_entry_created_by_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_filter_entry_created_by_id_seq OWNED BY public.extraction_extractionquery_filter_created_by.id;


--
-- Name: extraction_extractionquery_filter_entry_publishers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery_filter_entry_publishers (
    id integer NOT NULL,
    extractionquery_id integer NOT NULL,
    organization_id integer NOT NULL
);


--
-- Name: extraction_extractionquery_filter_entry_publishers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_filter_entry_publishers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_filter_entry_publishers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_filter_entry_publishers_id_seq OWNED BY public.extraction_extractionquery_filter_entry_publishers.id;


--
-- Name: extraction_extractionquery_filter_figure_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery_filter_figure_sources (
    id integer NOT NULL,
    extractionquery_id integer NOT NULL,
    organization_id integer NOT NULL
);


--
-- Name: extraction_extractionquery_filter_entry_sources_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_filter_entry_sources_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_filter_entry_sources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_filter_entry_sources_id_seq OWNED BY public.extraction_extractionquery_filter_figure_sources.id;


--
-- Name: extraction_extractionquery_filter_figure_disaster_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery_filter_figure_disaster_categories (
    id integer NOT NULL,
    extractionquery_id integer NOT NULL,
    disastercategory_id integer NOT NULL
);


--
-- Name: extraction_extractionquery_filter_event_disaster_categor_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_filter_event_disaster_categor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_filter_event_disaster_categor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_filter_event_disaster_categor_id_seq OWNED BY public.extraction_extractionquery_filter_figure_disaster_categories.id;


--
-- Name: extraction_extractionquery_filter_figure_disaster_sub_categf349; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery_filter_figure_disaster_sub_categf349 (
    id integer NOT NULL,
    extractionquery_id integer NOT NULL,
    disastersubcategory_id integer NOT NULL
);


--
-- Name: extraction_extractionquery_filter_event_disaster_sub_cat_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_filter_event_disaster_sub_cat_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_filter_event_disaster_sub_cat_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_filter_event_disaster_sub_cat_id_seq OWNED BY public.extraction_extractionquery_filter_figure_disaster_sub_categf349.id;


--
-- Name: extraction_extractionquery_filter_figure_disaster_sub_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery_filter_figure_disaster_sub_types (
    id integer NOT NULL,
    extractionquery_id integer NOT NULL,
    disastersubtype_id integer NOT NULL
);


--
-- Name: extraction_extractionquery_filter_event_disaster_sub_typ_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_filter_event_disaster_sub_typ_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_filter_event_disaster_sub_typ_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_filter_event_disaster_sub_typ_id_seq OWNED BY public.extraction_extractionquery_filter_figure_disaster_sub_types.id;


--
-- Name: extraction_extractionquery_filter_figure_disaster_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery_filter_figure_disaster_types (
    id integer NOT NULL,
    extractionquery_id integer NOT NULL,
    disastertype_id integer NOT NULL
);


--
-- Name: extraction_extractionquery_filter_event_disaster_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_filter_event_disaster_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_filter_event_disaster_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_filter_event_disaster_types_id_seq OWNED BY public.extraction_extractionquery_filter_figure_disaster_types.id;


--
-- Name: extraction_extractionquery_filter_figure_violence_sub_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery_filter_figure_violence_sub_types (
    id integer NOT NULL,
    extractionquery_id integer NOT NULL,
    violencesubtype_id integer NOT NULL
);


--
-- Name: extraction_extractionquery_filter_event_violence_sub_typ_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_filter_event_violence_sub_typ_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_filter_event_violence_sub_typ_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_filter_event_violence_sub_typ_id_seq OWNED BY public.extraction_extractionquery_filter_figure_violence_sub_types.id;


--
-- Name: extraction_extractionquery_filter_figure_violence_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery_filter_figure_violence_types (
    id integer NOT NULL,
    extractionquery_id integer NOT NULL,
    violence_id integer NOT NULL
);


--
-- Name: extraction_extractionquery_filter_event_violence_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_filter_event_violence_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_filter_event_violence_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_filter_event_violence_types_id_seq OWNED BY public.extraction_extractionquery_filter_figure_violence_types.id;


--
-- Name: extraction_extractionquery_filter_figure_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery_filter_figure_events (
    id integer NOT NULL,
    extractionquery_id integer NOT NULL,
    event_id integer NOT NULL
);


--
-- Name: extraction_extractionquery_filter_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_filter_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_filter_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_filter_events_id_seq OWNED BY public.extraction_extractionquery_filter_figure_events.id;


--
-- Name: extraction_extractionquery_filter_figure_countries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery_filter_figure_countries (
    id integer NOT NULL,
    extractionquery_id integer NOT NULL,
    country_id integer NOT NULL
);


--
-- Name: extraction_extractionquery_filter_figure_countries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_filter_figure_countries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_filter_figure_countries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_filter_figure_countries_id_seq OWNED BY public.extraction_extractionquery_filter_figure_countries.id;


--
-- Name: extraction_extractionquery_filter_figure_crises; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery_filter_figure_crises (
    id integer NOT NULL,
    extractionquery_id integer NOT NULL,
    crisis_id integer NOT NULL
);


--
-- Name: extraction_extractionquery_filter_figure_crises_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_filter_figure_crises_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_filter_figure_crises_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_filter_figure_crises_id_seq OWNED BY public.extraction_extractionquery_filter_figure_crises.id;


--
-- Name: extraction_extractionquery_filter_figure_geographical_groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery_filter_figure_geographical_groups (
    id integer NOT NULL,
    extractionquery_id integer NOT NULL,
    geographicalgroup_id integer NOT NULL
);


--
-- Name: extraction_extractionquery_filter_figure_geographical_gr_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_filter_figure_geographical_gr_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_filter_figure_geographical_gr_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_filter_figure_geographical_gr_id_seq OWNED BY public.extraction_extractionquery_filter_figure_geographical_groups.id;


--
-- Name: extraction_extractionquery_filter_figure_regions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery_filter_figure_regions (
    id integer NOT NULL,
    extractionquery_id integer NOT NULL,
    countryregion_id integer NOT NULL
);


--
-- Name: extraction_extractionquery_filter_figure_regions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_filter_figure_regions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_filter_figure_regions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_filter_figure_regions_id_seq OWNED BY public.extraction_extractionquery_filter_figure_regions.id;


--
-- Name: extraction_extractionquery_filter_figure_tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_extractionquery_filter_figure_tags (
    id integer NOT NULL,
    extractionquery_id integer NOT NULL,
    figuretag_id integer NOT NULL
);


--
-- Name: extraction_extractionquery_filter_figure_tags_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_filter_figure_tags_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_filter_figure_tags_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_filter_figure_tags_id_seq OWNED BY public.extraction_extractionquery_filter_figure_tags.id;


--
-- Name: extraction_extractionquery_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_extractionquery_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_extractionquery_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_extractionquery_id_seq OWNED BY public.extraction_extractionquery.id;


--
-- Name: gidd_conflict; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gidd_conflict (
    id integer NOT NULL,
    total_displacement bigint,
    new_displacement bigint,
    year integer NOT NULL,
    country_name character varying(256) NOT NULL,
    iso3 character varying(5) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    country_id integer NOT NULL,
    new_displacement_rounded bigint,
    total_displacement_rounded bigint
);


--
-- Name: gidd_conflict_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gidd_conflict_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gidd_conflict_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gidd_conflict_id_seq OWNED BY public.gidd_conflict.id;


--
-- Name: gidd_conflictlegacy; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gidd_conflictlegacy (
    id integer NOT NULL,
    total_displacement bigint,
    new_displacement bigint,
    year integer NOT NULL,
    iso3 character varying(5) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: gidd_conflictlegacy_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gidd_conflictlegacy_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gidd_conflictlegacy_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gidd_conflictlegacy_id_seq OWNED BY public.gidd_conflictlegacy.id;


--
-- Name: gidd_disaster; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gidd_disaster (
    id integer NOT NULL,
    year integer NOT NULL,
    country_name character varying(256) NOT NULL,
    iso3 character varying(5) NOT NULL,
    start_date date,
    start_date_accuracy text,
    end_date date,
    end_date_accuracy text,
    hazard_category_id integer NOT NULL,
    hazard_sub_category_id integer NOT NULL,
    hazard_sub_type_id integer NOT NULL,
    hazard_type_id integer NOT NULL,
    new_displacement bigint,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    event_id integer,
    country_id integer NOT NULL,
    event_name character varying(256) NOT NULL,
    hazard_category_name character varying(256) NOT NULL,
    hazard_sub_category_name character varying(256) NOT NULL,
    hazard_sub_type_name character varying(256) NOT NULL,
    hazard_type_name character varying(256) NOT NULL,
    total_displacement bigint,
    glide_numbers character varying(256)[] NOT NULL,
    new_displacement_rounded bigint,
    total_displacement_rounded bigint
);


--
-- Name: gidd_disaster_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gidd_disaster_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gidd_disaster_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gidd_disaster_id_seq OWNED BY public.gidd_disaster.id;


--
-- Name: gidd_disasterlegacy; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gidd_disasterlegacy (
    id integer NOT NULL,
    year integer NOT NULL,
    iso3 character varying(5) NOT NULL,
    event_name character varying(256) NOT NULL,
    start_date date,
    start_date_accuracy text,
    end_date date,
    end_date_accuracy text,
    hazard_category_id integer NOT NULL,
    hazard_sub_category_id integer NOT NULL,
    hazard_sub_type_id integer NOT NULL,
    hazard_type_id integer NOT NULL,
    new_displacement bigint,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: gidd_disasterlegacy_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gidd_disasterlegacy_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gidd_disasterlegacy_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gidd_disasterlegacy_id_seq OWNED BY public.gidd_disasterlegacy.id;


--
-- Name: gidd_displacementdata; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gidd_displacementdata (
    id integer NOT NULL,
    iso3 character varying(5) NOT NULL,
    country_name character varying(256) NOT NULL,
    year integer NOT NULL,
    country_id integer NOT NULL,
    conflict_new_displacement bigint,
    conflict_total_displacement bigint,
    disaster_new_displacement bigint,
    disaster_total_displacement bigint,
    conflict_new_displacement_rounded bigint,
    conflict_total_displacement_rounded bigint,
    disaster_new_displacement_rounded bigint,
    disaster_total_displacement_rounded bigint
);


--
-- Name: gidd_displacementdata_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gidd_displacementdata_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gidd_displacementdata_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gidd_displacementdata_id_seq OWNED BY public.gidd_displacementdata.id;


--
-- Name: gidd_statuslog; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gidd_statuslog (
    id integer NOT NULL,
    triggered_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    status integer NOT NULL,
    triggered_by_id integer NOT NULL
);


--
-- Name: gidd_giddlog_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gidd_giddlog_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gidd_giddlog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gidd_giddlog_id_seq OWNED BY public.gidd_statuslog.id;


--
-- Name: gidd_idpssaddestimate; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gidd_idpssaddestimate (
    id integer NOT NULL,
    iso3 character varying(5) NOT NULL,
    country_name character varying(256) NOT NULL,
    year integer NOT NULL,
    sex character varying(256) NOT NULL,
    cause integer NOT NULL,
    zero_to_one integer,
    zero_to_four integer,
    zero_to_forteen integer,
    zero_to_sventeen integer,
    zero_to_twenty_four integer,
    five_to_elaven integer,
    five_to_fourteen integer,
    twelve_to_fourteen integer,
    twelve_to_sixteen integer,
    fifteen_to_seventeen integer,
    fifteen_to_twentyfour integer,
    twenty_five_to_sixty_four integer,
    sixty_five_plus integer,
    country_id integer NOT NULL
);


--
-- Name: gidd_idpssaddestimate_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gidd_idpssaddestimate_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gidd_idpssaddestimate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gidd_idpssaddestimate_id_seq OWNED BY public.gidd_idpssaddestimate.id;


--
-- Name: gidd_publicfigureanalysis; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gidd_publicfigureanalysis (
    id integer NOT NULL,
    iso3 character varying(5) NOT NULL,
    figure_cause integer NOT NULL,
    figure_category integer NOT NULL,
    year integer NOT NULL,
    figures integer,
    description text,
    report_id integer,
    figures_rounded integer
);


--
-- Name: gidd_publicfigureanalysis_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gidd_publicfigureanalysis_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gidd_publicfigureanalysis_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gidd_publicfigureanalysis_id_seq OWNED BY public.gidd_publicfigureanalysis.id;


--
-- Name: gidd_releasemetadata; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gidd_releasemetadata (
    id integer NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    modified_by_id integer NOT NULL,
    pre_release_year integer NOT NULL,
    release_year integer NOT NULL
);


--
-- Name: gidd_releasemetadata_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gidd_releasemetadata_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gidd_releasemetadata_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gidd_releasemetadata_id_seq OWNED BY public.gidd_releasemetadata.id;


--
-- Name: gidd_statuslog_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gidd_statuslog_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gidd_statuslog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gidd_statuslog_id_seq OWNED BY public.gidd_statuslog.id;


--
-- Name: organization_organization; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organization_organization (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    name character varying(512) NOT NULL,
    short_name character varying(64),
    methodology text,
    created_by_id integer,
    last_modified_by_id integer,
    organization_kind_id integer,
    parent_id integer,
    breakdown text,
    deleted_on timestamp with time zone,
    old_id character varying(32),
    category integer NOT NULL
);


--
-- Name: organization_organization_countries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organization_organization_countries (
    id integer NOT NULL,
    organization_id integer NOT NULL,
    country_id integer NOT NULL
);


--
-- Name: organization_organization_countries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.organization_organization_countries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: organization_organization_countries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.organization_organization_countries_id_seq OWNED BY public.organization_organization_countries.id;


--
-- Name: organization_organization_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.organization_organization_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: organization_organization_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.organization_organization_id_seq OWNED BY public.organization_organization.id;


--
-- Name: organization_organizationkind; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organization_organizationkind (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    name character varying(256) NOT NULL,
    created_by_id integer,
    last_modified_by_id integer,
    old_id character varying(32)
);


--
-- Name: organization_organizationkind_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.organization_organizationkind_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: organization_organizationkind_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.organization_organizationkind_id_seq OWNED BY public.organization_organizationkind.id;


--
-- Name: parking_lot_parkeditem; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parking_lot_parkeditem (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    title text NOT NULL,
    url character varying(200) NOT NULL,
    status integer NOT NULL,
    comments text,
    assigned_to_id integer,
    country_id integer NOT NULL,
    created_by_id integer,
    last_modified_by_id integer
);


--
-- Name: parking_lot_parkeditem_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.parking_lot_parkeditem_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: parking_lot_parkeditem_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.parking_lot_parkeditem_id_seq OWNED BY public.parking_lot_parkeditem.id;


--
-- Name: report_report; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report (
    id integer NOT NULL,
    old_id character varying(32),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    disaggregation_displacement_urban integer,
    disaggregation_displacement_rural integer,
    disaggregation_location_camp integer,
    disaggregation_location_non_camp integer,
    disaggregation_sex_male integer,
    disaggregation_sex_female integer,
    disaggregation_strata_json jsonb[],
    disaggregation_conflict integer,
    disaggregation_conflict_political integer,
    disaggregation_conflict_criminal integer,
    disaggregation_conflict_communal integer,
    disaggregation_conflict_other integer,
    name character varying(128) NOT NULL,
    filter_figure_start_after date,
    filter_figure_end_before date,
    filter_figure_roles integer[],
    filter_entry_article_title text,
    generated boolean NOT NULL,
    analysis text,
    methodology text,
    significant_updates text,
    challenges text,
    reported integer NOT NULL,
    total_figures integer NOT NULL,
    summary text,
    created_by_id integer,
    last_modified_by_id integer,
    filter_figure_crisis_types integer[],
    generated_from integer,
    is_signed_off boolean NOT NULL,
    is_signed_off_by_id integer,
    filter_figure_glide_number character varying(100)[],
    filter_figure_displacement_types integer[],
    disaggregation_disability integer,
    disaggregation_indigenous_people integer,
    disaggregation_lgbtiq integer,
    filter_figure_category_types character varying(8)[],
    is_public boolean NOT NULL,
    filter_figure_has_disaggregated_data boolean,
    filter_figure_categories integer[],
    filter_figure_terms integer[],
    filter_figure_review_status integer[],
    filter_is_figure_to_be_reviewed boolean,
    public_figure_analysis text,
    is_pfa_visible_in_gidd boolean NOT NULL,
    gidd_report_year integer,
    is_gidd_report boolean NOT NULL,
    CONSTRAINT report_report_disaggregation_conflict_c0d17a58_check CHECK ((disaggregation_conflict >= 0)),
    CONSTRAINT report_report_disaggregation_conflict_communal_2906f160_check CHECK ((disaggregation_conflict_communal >= 0)),
    CONSTRAINT report_report_disaggregation_conflict_criminal_42ac717a_check CHECK ((disaggregation_conflict_criminal >= 0)),
    CONSTRAINT report_report_disaggregation_conflict_other_76788493_check CHECK ((disaggregation_conflict_other >= 0)),
    CONSTRAINT report_report_disaggregation_conflict_political_fe416246_check CHECK ((disaggregation_conflict_political >= 0)),
    CONSTRAINT report_report_disaggregation_disability_check CHECK ((disaggregation_disability >= 0)),
    CONSTRAINT report_report_disaggregation_displacement_rural_ae384cf6_check CHECK ((disaggregation_displacement_rural >= 0)),
    CONSTRAINT report_report_disaggregation_displacement_urban_48b2d50b_check CHECK ((disaggregation_displacement_urban >= 0)),
    CONSTRAINT report_report_disaggregation_indigenous_people_check CHECK ((disaggregation_indigenous_people >= 0)),
    CONSTRAINT report_report_disaggregation_lgbtiq_check CHECK ((disaggregation_lgbtiq >= 0)),
    CONSTRAINT report_report_disaggregation_location_camp_7281b343_check CHECK ((disaggregation_location_camp >= 0)),
    CONSTRAINT report_report_disaggregation_location_non_camp_403b30ae_check CHECK ((disaggregation_location_non_camp >= 0)),
    CONSTRAINT report_report_disaggregation_sex_female_c0c3a584_check CHECK ((disaggregation_sex_female >= 0)),
    CONSTRAINT report_report_disaggregation_sex_male_56cd0863_check CHECK ((disaggregation_sex_male >= 0)),
    CONSTRAINT report_report_gidd_report_year_check CHECK ((gidd_report_year >= 0)),
    CONSTRAINT report_report_reported_check CHECK ((reported >= 0)),
    CONSTRAINT report_report_total_figures_check CHECK ((total_figures >= 0))
);


--
-- Name: report_report_disaggregation_age; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_disaggregation_age (
    id integer NOT NULL,
    report_id integer NOT NULL,
    disaggregatedage_id integer NOT NULL
);


--
-- Name: report_report_disaggregation_age_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_disaggregation_age_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_disaggregation_age_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_disaggregation_age_id_seq OWNED BY public.report_report_disaggregation_age.id;


--
-- Name: report_report_figures; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_figures (
    id integer NOT NULL,
    report_id integer NOT NULL,
    figure_id integer NOT NULL
);


--
-- Name: report_report_figures_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_figures_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_figures_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_figures_id_seq OWNED BY public.report_report_figures.id;


--
-- Name: report_report_filter_context_of_violence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_filter_context_of_violence (
    id integer NOT NULL,
    report_id integer NOT NULL,
    contextofviolence_id integer NOT NULL
);


--
-- Name: report_report_filter_context_of_violence_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_filter_context_of_violence_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_filter_context_of_violence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_filter_context_of_violence_id_seq OWNED BY public.report_report_filter_context_of_violence.id;


--
-- Name: report_report_filter_created_by; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_filter_created_by (
    id integer NOT NULL,
    report_id integer NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: report_report_filter_entry_created_by_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_filter_entry_created_by_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_filter_entry_created_by_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_filter_entry_created_by_id_seq OWNED BY public.report_report_filter_created_by.id;


--
-- Name: report_report_filter_entry_publishers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_filter_entry_publishers (
    id integer NOT NULL,
    report_id integer NOT NULL,
    organization_id integer NOT NULL
);


--
-- Name: report_report_filter_entry_publishers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_filter_entry_publishers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_filter_entry_publishers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_filter_entry_publishers_id_seq OWNED BY public.report_report_filter_entry_publishers.id;


--
-- Name: report_report_filter_figure_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_filter_figure_sources (
    id integer NOT NULL,
    report_id integer NOT NULL,
    organization_id integer NOT NULL
);


--
-- Name: report_report_filter_entry_sources_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_filter_entry_sources_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_filter_entry_sources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_filter_entry_sources_id_seq OWNED BY public.report_report_filter_figure_sources.id;


--
-- Name: report_report_filter_figure_disaster_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_filter_figure_disaster_categories (
    id integer NOT NULL,
    report_id integer NOT NULL,
    disastercategory_id integer NOT NULL
);


--
-- Name: report_report_filter_event_disaster_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_filter_event_disaster_categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_filter_event_disaster_categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_filter_event_disaster_categories_id_seq OWNED BY public.report_report_filter_figure_disaster_categories.id;


--
-- Name: report_report_filter_figure_disaster_sub_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_filter_figure_disaster_sub_categories (
    id integer NOT NULL,
    report_id integer NOT NULL,
    disastersubcategory_id integer NOT NULL
);


--
-- Name: report_report_filter_event_disaster_sub_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_filter_event_disaster_sub_categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_filter_event_disaster_sub_categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_filter_event_disaster_sub_categories_id_seq OWNED BY public.report_report_filter_figure_disaster_sub_categories.id;


--
-- Name: report_report_filter_figure_disaster_sub_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_filter_figure_disaster_sub_types (
    id integer NOT NULL,
    report_id integer NOT NULL,
    disastersubtype_id integer NOT NULL
);


--
-- Name: report_report_filter_event_disaster_sub_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_filter_event_disaster_sub_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_filter_event_disaster_sub_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_filter_event_disaster_sub_types_id_seq OWNED BY public.report_report_filter_figure_disaster_sub_types.id;


--
-- Name: report_report_filter_figure_disaster_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_filter_figure_disaster_types (
    id integer NOT NULL,
    report_id integer NOT NULL,
    disastertype_id integer NOT NULL
);


--
-- Name: report_report_filter_event_disaster_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_filter_event_disaster_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_filter_event_disaster_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_filter_event_disaster_types_id_seq OWNED BY public.report_report_filter_figure_disaster_types.id;


--
-- Name: report_report_filter_figure_violence_sub_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_filter_figure_violence_sub_types (
    id integer NOT NULL,
    report_id integer NOT NULL,
    violencesubtype_id integer NOT NULL
);


--
-- Name: report_report_filter_event_violence_sub_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_filter_event_violence_sub_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_filter_event_violence_sub_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_filter_event_violence_sub_types_id_seq OWNED BY public.report_report_filter_figure_violence_sub_types.id;


--
-- Name: report_report_filter_figure_violence_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_filter_figure_violence_types (
    id integer NOT NULL,
    report_id integer NOT NULL,
    violence_id integer NOT NULL
);


--
-- Name: report_report_filter_event_violence_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_filter_event_violence_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_filter_event_violence_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_filter_event_violence_types_id_seq OWNED BY public.report_report_filter_figure_violence_types.id;


--
-- Name: report_report_filter_figure_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_filter_figure_events (
    id integer NOT NULL,
    report_id integer NOT NULL,
    event_id integer NOT NULL
);


--
-- Name: report_report_filter_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_filter_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_filter_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_filter_events_id_seq OWNED BY public.report_report_filter_figure_events.id;


--
-- Name: report_report_filter_figure_countries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_filter_figure_countries (
    id integer NOT NULL,
    report_id integer NOT NULL,
    country_id integer NOT NULL
);


--
-- Name: report_report_filter_figure_countries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_filter_figure_countries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_filter_figure_countries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_filter_figure_countries_id_seq OWNED BY public.report_report_filter_figure_countries.id;


--
-- Name: report_report_filter_figure_crises; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_filter_figure_crises (
    id integer NOT NULL,
    report_id integer NOT NULL,
    crisis_id integer NOT NULL
);


--
-- Name: report_report_filter_figure_crises_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_filter_figure_crises_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_filter_figure_crises_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_filter_figure_crises_id_seq OWNED BY public.report_report_filter_figure_crises.id;


--
-- Name: report_report_filter_figure_geographical_groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_filter_figure_geographical_groups (
    id integer NOT NULL,
    report_id integer NOT NULL,
    geographicalgroup_id integer NOT NULL
);


--
-- Name: report_report_filter_figure_geographical_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_filter_figure_geographical_groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_filter_figure_geographical_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_filter_figure_geographical_groups_id_seq OWNED BY public.report_report_filter_figure_geographical_groups.id;


--
-- Name: report_report_filter_figure_regions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_filter_figure_regions (
    id integer NOT NULL,
    report_id integer NOT NULL,
    countryregion_id integer NOT NULL
);


--
-- Name: report_report_filter_figure_regions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_filter_figure_regions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_filter_figure_regions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_filter_figure_regions_id_seq OWNED BY public.report_report_filter_figure_regions.id;


--
-- Name: report_report_filter_figure_tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_filter_figure_tags (
    id integer NOT NULL,
    report_id integer NOT NULL,
    figuretag_id integer NOT NULL
);


--
-- Name: report_report_filter_figure_tags_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_filter_figure_tags_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_filter_figure_tags_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_filter_figure_tags_id_seq OWNED BY public.report_report_filter_figure_tags.id;


--
-- Name: report_report_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_id_seq OWNED BY public.report_report.id;


--
-- Name: report_report_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_report_reports (
    id integer NOT NULL,
    from_report_id integer NOT NULL,
    to_report_id integer NOT NULL
);


--
-- Name: report_report_reports_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_report_reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_report_reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_report_reports_id_seq OWNED BY public.report_report_reports.id;


--
-- Name: report_reportapproval; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_reportapproval (
    id integer NOT NULL,
    old_id character varying(32),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    is_approved boolean NOT NULL,
    created_by_id integer NOT NULL,
    generation_id integer NOT NULL,
    last_modified_by_id integer
);


--
-- Name: report_reportapproval_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_reportapproval_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_reportapproval_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_reportapproval_id_seq OWNED BY public.report_reportapproval.id;


--
-- Name: report_reportcomment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_reportcomment (
    id integer NOT NULL,
    old_id character varying(32),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    body text NOT NULL,
    created_by_id integer,
    last_modified_by_id integer,
    report_id integer NOT NULL
);


--
-- Name: report_reportcomment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_reportcomment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_reportcomment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_reportcomment_id_seq OWNED BY public.report_reportcomment.id;


--
-- Name: report_reportgeneration; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_reportgeneration (
    id integer NOT NULL,
    old_id character varying(32),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    version_id character varying(16),
    is_signed_off boolean NOT NULL,
    full_report character varying(256),
    snapshot character varying(256),
    created_by_id integer,
    is_signed_off_by_id integer,
    last_modified_by_id integer,
    report_id integer NOT NULL,
    status integer NOT NULL,
    is_signed_off_on timestamp with time zone,
    include_history boolean NOT NULL,
    completed_at timestamp with time zone,
    started_at timestamp with time zone
);


--
-- Name: report_reportgeneration_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_reportgeneration_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_reportgeneration_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_reportgeneration_id_seq OWNED BY public.report_reportgeneration.id;


--
-- Name: users_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users_user (
    id integer NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    first_name character varying(30) NOT NULL,
    last_name character varying(150) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL,
    email character varying(254) NOT NULL,
    username character varying(150) NOT NULL
);


--
-- Name: users_user_groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users_user_groups (
    id integer NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


--
-- Name: users_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_user_groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_user_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_user_groups_id_seq OWNED BY public.users_user_groups.id;


--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users_user.id;


--
-- Name: users_user_user_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users_user_user_permissions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


--
-- Name: users_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_user_user_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_user_user_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_user_user_permissions_id_seq OWNED BY public.users_user_user_permissions.id;


--
-- Name: auth_group id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group ALTER COLUMN id SET DEFAULT nextval('public.auth_group_id_seq'::regclass);


--
-- Name: auth_group_permissions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions ALTER COLUMN id SET DEFAULT nextval('public.auth_group_permissions_id_seq'::regclass);


--
-- Name: auth_permission id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_permission ALTER COLUMN id SET DEFAULT nextval('public.auth_permission_id_seq'::regclass);


--
-- Name: contact_communication id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_communication ALTER COLUMN id SET DEFAULT nextval('public.contact_communication_id_seq'::regclass);


--
-- Name: contact_communicationmedium id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_communicationmedium ALTER COLUMN id SET DEFAULT nextval('public.contact_communicationmedium_id_seq'::regclass);


--
-- Name: contact_contact id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_contact ALTER COLUMN id SET DEFAULT nextval('public.contact_contact_id_seq'::regclass);


--
-- Name: contact_contact_countries_of_operation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_contact_countries_of_operation ALTER COLUMN id SET DEFAULT nextval('public.contact_contact_countries_of_operation_id_seq'::regclass);


--
-- Name: contextualupdate_contextualupdate id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate ALTER COLUMN id SET DEFAULT nextval('public.contextualupdate_contextualupdate_id_seq'::regclass);


--
-- Name: contextualupdate_contextualupdate_countries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_countries ALTER COLUMN id SET DEFAULT nextval('public.contextualupdate_contextualupdate_countries_id_seq'::regclass);


--
-- Name: contextualupdate_contextualupdate_publishers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_publishers ALTER COLUMN id SET DEFAULT nextval('public.contextualupdate_contextualupdate_publishers_id_seq'::regclass);


--
-- Name: contextualupdate_contextualupdate_sources id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_sources ALTER COLUMN id SET DEFAULT nextval('public.contextualupdate_contextualupdate_sources_id_seq'::regclass);


--
-- Name: contextualupdate_contextualupdate_tags id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_tags ALTER COLUMN id SET DEFAULT nextval('public.contextualupdate_contextualupdate_tags_id_seq'::regclass);


--
-- Name: contrib_attachment id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_attachment ALTER COLUMN id SET DEFAULT nextval('public.contrib_attachment_id_seq'::regclass);


--
-- Name: contrib_bulkapioperation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_bulkapioperation ALTER COLUMN id SET DEFAULT nextval('public.contrib_bulkapioperation_id_seq'::regclass);


--
-- Name: contrib_client id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_client ALTER COLUMN id SET DEFAULT nextval('public.contrib_client_id_seq'::regclass);


--
-- Name: contrib_clienttrackinfo id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_clienttrackinfo ALTER COLUMN id SET DEFAULT nextval('public.contrib_clienttrackinfo_id_seq'::regclass);


--
-- Name: contrib_exceldownload id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_exceldownload ALTER COLUMN id SET DEFAULT nextval('public.contrib_exceldownload_id_seq'::regclass);


--
-- Name: contrib_sourcepreview id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_sourcepreview ALTER COLUMN id SET DEFAULT nextval('public.contrib_sourcepreview_id_seq'::regclass);


--
-- Name: country_contextualanalysis id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_contextualanalysis ALTER COLUMN id SET DEFAULT nextval('public.country_contextualanalysis_id_seq'::regclass);


--
-- Name: country_country id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_country ALTER COLUMN id SET DEFAULT nextval('public.country_country_id_seq'::regclass);


--
-- Name: country_countrypopulation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_countrypopulation ALTER COLUMN id SET DEFAULT nextval('public.country_countrypopulation_id_seq'::regclass);


--
-- Name: country_countryregion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_countryregion ALTER COLUMN id SET DEFAULT nextval('public.country_countryregion_id_seq'::regclass);


--
-- Name: country_countrysubregion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_countrysubregion ALTER COLUMN id SET DEFAULT nextval('public.country_countrysubregion_id_seq'::regclass);


--
-- Name: country_geographicalgroup id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_geographicalgroup ALTER COLUMN id SET DEFAULT nextval('public.country_geographicalgroup_id_seq'::regclass);


--
-- Name: country_householdsize id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_householdsize ALTER COLUMN id SET DEFAULT nextval('public.country_householdsize_id_seq'::regclass);


--
-- Name: country_monitoringsubregion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_monitoringsubregion ALTER COLUMN id SET DEFAULT nextval('public.country_monitoringsubregion_id_seq'::regclass);


--
-- Name: country_summary id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_summary ALTER COLUMN id SET DEFAULT nextval('public.country_summary_id_seq'::regclass);


--
-- Name: crisis_crisis id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crisis_crisis ALTER COLUMN id SET DEFAULT nextval('public.crisis_crisis_id_seq'::regclass);


--
-- Name: crisis_crisis_countries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crisis_crisis_countries ALTER COLUMN id SET DEFAULT nextval('public.crisis_crisis_countries_id_seq'::regclass);


--
-- Name: django_admin_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_admin_log ALTER COLUMN id SET DEFAULT nextval('public.django_admin_log_id_seq'::regclass);


--
-- Name: django_content_type id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_content_type ALTER COLUMN id SET DEFAULT nextval('public.django_content_type_id_seq'::regclass);


--
-- Name: django_migrations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_migrations ALTER COLUMN id SET DEFAULT nextval('public.django_migrations_id_seq'::regclass);


--
-- Name: entry_disaggregatedage id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_disaggregatedage ALTER COLUMN id SET DEFAULT nextval('public.entry_disaggregatedage_id_seq'::regclass);


--
-- Name: entry_entry id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entry ALTER COLUMN id SET DEFAULT nextval('public.entry_entry_id_seq'::regclass);


--
-- Name: entry_entry_publishers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entry_publishers ALTER COLUMN id SET DEFAULT nextval('public.entry_entry_publishers_id_seq'::regclass);


--
-- Name: entry_entryreviewer id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entryreviewer ALTER COLUMN id SET DEFAULT nextval('public.entry_entryreviewer_id_seq'::regclass);


--
-- Name: entry_externalapidump id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_externalapidump ALTER COLUMN id SET DEFAULT nextval('public.entry_externalapidump_id_seq'::regclass);


--
-- Name: entry_figure id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure ALTER COLUMN id SET DEFAULT nextval('public.entry_figure_id_seq'::regclass);


--
-- Name: entry_figure_context_of_violence id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_context_of_violence ALTER COLUMN id SET DEFAULT nextval('public.entry_figure_context_of_violence_id_seq'::regclass);


--
-- Name: entry_figure_disaggregation_age id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_disaggregation_age ALTER COLUMN id SET DEFAULT nextval('public.entry_figure_disaggregation_age_id_seq'::regclass);


--
-- Name: entry_figure_geo_locations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_geo_locations ALTER COLUMN id SET DEFAULT nextval('public.entry_figure_geo_locations_id_seq'::regclass);


--
-- Name: entry_figure_sources id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_sources ALTER COLUMN id SET DEFAULT nextval('public.entry_figure_sources_id_seq'::regclass);


--
-- Name: entry_figure_tags id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_tags ALTER COLUMN id SET DEFAULT nextval('public.entry_figure_tags_id_seq'::regclass);


--
-- Name: entry_figuretag id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figuretag ALTER COLUMN id SET DEFAULT nextval('public.entry_figuretag_id_seq'::regclass);


--
-- Name: entry_osmname id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_osmname ALTER COLUMN id SET DEFAULT nextval('public.entry_osmname_id_seq'::regclass);


--
-- Name: event_actor id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_actor ALTER COLUMN id SET DEFAULT nextval('public.event_actor_id_seq'::regclass);


--
-- Name: event_contextofviolence id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_contextofviolence ALTER COLUMN id SET DEFAULT nextval('public.event_contextofviolence_id_seq'::regclass);


--
-- Name: event_disastercategory id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_disastercategory ALTER COLUMN id SET DEFAULT nextval('public.event_disastercategory_id_seq'::regclass);


--
-- Name: event_disastersubcategory id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_disastersubcategory ALTER COLUMN id SET DEFAULT nextval('public.event_disastersubcategory_id_seq'::regclass);


--
-- Name: event_disastersubtype id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_disastersubtype ALTER COLUMN id SET DEFAULT nextval('public.event_disastersubtype_id_seq'::regclass);


--
-- Name: event_disastertype id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_disastertype ALTER COLUMN id SET DEFAULT nextval('public.event_disastertype_id_seq'::regclass);


--
-- Name: event_event id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event ALTER COLUMN id SET DEFAULT nextval('public.event_event_id_seq'::regclass);


--
-- Name: event_event_context_of_violence id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event_context_of_violence ALTER COLUMN id SET DEFAULT nextval('public.event_event_context_of_violence_id_seq'::regclass);


--
-- Name: event_event_countries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event_countries ALTER COLUMN id SET DEFAULT nextval('public.event_event_countries_id_seq'::regclass);


--
-- Name: event_eventcode id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_eventcode ALTER COLUMN id SET DEFAULT nextval('public.event_eventcode_id_seq'::regclass);


--
-- Name: event_osvsubtype id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_osvsubtype ALTER COLUMN id SET DEFAULT nextval('public.event_osvsubtype_id_seq'::regclass);


--
-- Name: event_othersubtype id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_othersubtype ALTER COLUMN id SET DEFAULT nextval('public.event_othersubtype_id_seq'::regclass);


--
-- Name: event_violence id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_violence ALTER COLUMN id SET DEFAULT nextval('public.event_violence_id_seq'::regclass);


--
-- Name: event_violencesubtype id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_violencesubtype ALTER COLUMN id SET DEFAULT nextval('public.event_violencesubtype_id_seq'::regclass);


--
-- Name: extraction_extractionquery id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_id_seq'::regclass);


--
-- Name: extraction_extractionquery_filter_context_of_violence id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_context_of_violence ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_filter_context_of_violence_id_seq'::regclass);


--
-- Name: extraction_extractionquery_filter_created_by id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_created_by ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_filter_entry_created_by_id_seq'::regclass);


--
-- Name: extraction_extractionquery_filter_entry_publishers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_entry_publishers ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_filter_entry_publishers_id_seq'::regclass);


--
-- Name: extraction_extractionquery_filter_figure_countries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_countries ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_filter_figure_countries_id_seq'::regclass);


--
-- Name: extraction_extractionquery_filter_figure_crises id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_crises ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_filter_figure_crises_id_seq'::regclass);


--
-- Name: extraction_extractionquery_filter_figure_disaster_categories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_categories ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_filter_event_disaster_categor_id_seq'::regclass);


--
-- Name: extraction_extractionquery_filter_figure_disaster_sub_categf349 id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_sub_categf349 ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_filter_event_disaster_sub_cat_id_seq'::regclass);


--
-- Name: extraction_extractionquery_filter_figure_disaster_sub_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_sub_types ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_filter_event_disaster_sub_typ_id_seq'::regclass);


--
-- Name: extraction_extractionquery_filter_figure_disaster_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_types ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_filter_event_disaster_types_id_seq'::regclass);


--
-- Name: extraction_extractionquery_filter_figure_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_events ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_filter_events_id_seq'::regclass);


--
-- Name: extraction_extractionquery_filter_figure_geographical_groups id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_geographical_groups ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_filter_figure_geographical_gr_id_seq'::regclass);


--
-- Name: extraction_extractionquery_filter_figure_regions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_regions ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_filter_figure_regions_id_seq'::regclass);


--
-- Name: extraction_extractionquery_filter_figure_sources id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_sources ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_filter_entry_sources_id_seq'::regclass);


--
-- Name: extraction_extractionquery_filter_figure_tags id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_tags ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_filter_figure_tags_id_seq'::regclass);


--
-- Name: extraction_extractionquery_filter_figure_violence_sub_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_violence_sub_types ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_filter_event_violence_sub_typ_id_seq'::regclass);


--
-- Name: extraction_extractionquery_filter_figure_violence_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_violence_types ALTER COLUMN id SET DEFAULT nextval('public.extraction_extractionquery_filter_event_violence_types_id_seq'::regclass);


--
-- Name: gidd_conflict id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_conflict ALTER COLUMN id SET DEFAULT nextval('public.gidd_conflict_id_seq'::regclass);


--
-- Name: gidd_conflictlegacy id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_conflictlegacy ALTER COLUMN id SET DEFAULT nextval('public.gidd_conflictlegacy_id_seq'::regclass);


--
-- Name: gidd_disaster id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_disaster ALTER COLUMN id SET DEFAULT nextval('public.gidd_disaster_id_seq'::regclass);


--
-- Name: gidd_disasterlegacy id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_disasterlegacy ALTER COLUMN id SET DEFAULT nextval('public.gidd_disasterlegacy_id_seq'::regclass);


--
-- Name: gidd_displacementdata id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_displacementdata ALTER COLUMN id SET DEFAULT nextval('public.gidd_displacementdata_id_seq'::regclass);


--
-- Name: gidd_idpssaddestimate id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_idpssaddestimate ALTER COLUMN id SET DEFAULT nextval('public.gidd_idpssaddestimate_id_seq'::regclass);


--
-- Name: gidd_publicfigureanalysis id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_publicfigureanalysis ALTER COLUMN id SET DEFAULT nextval('public.gidd_publicfigureanalysis_id_seq'::regclass);


--
-- Name: gidd_releasemetadata id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_releasemetadata ALTER COLUMN id SET DEFAULT nextval('public.gidd_releasemetadata_id_seq'::regclass);


--
-- Name: gidd_statuslog id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_statuslog ALTER COLUMN id SET DEFAULT nextval('public.gidd_statuslog_id_seq'::regclass);


--
-- Name: organization_organization id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_organization ALTER COLUMN id SET DEFAULT nextval('public.organization_organization_id_seq'::regclass);


--
-- Name: organization_organization_countries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_organization_countries ALTER COLUMN id SET DEFAULT nextval('public.organization_organization_countries_id_seq'::regclass);


--
-- Name: organization_organizationkind id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_organizationkind ALTER COLUMN id SET DEFAULT nextval('public.organization_organizationkind_id_seq'::regclass);


--
-- Name: parking_lot_parkeditem id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parking_lot_parkeditem ALTER COLUMN id SET DEFAULT nextval('public.parking_lot_parkeditem_id_seq'::regclass);


--
-- Name: report_report id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report ALTER COLUMN id SET DEFAULT nextval('public.report_report_id_seq'::regclass);


--
-- Name: report_report_disaggregation_age id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_disaggregation_age ALTER COLUMN id SET DEFAULT nextval('public.report_report_disaggregation_age_id_seq'::regclass);


--
-- Name: report_report_figures id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_figures ALTER COLUMN id SET DEFAULT nextval('public.report_report_figures_id_seq'::regclass);


--
-- Name: report_report_filter_context_of_violence id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_context_of_violence ALTER COLUMN id SET DEFAULT nextval('public.report_report_filter_context_of_violence_id_seq'::regclass);


--
-- Name: report_report_filter_created_by id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_created_by ALTER COLUMN id SET DEFAULT nextval('public.report_report_filter_entry_created_by_id_seq'::regclass);


--
-- Name: report_report_filter_entry_publishers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_entry_publishers ALTER COLUMN id SET DEFAULT nextval('public.report_report_filter_entry_publishers_id_seq'::regclass);


--
-- Name: report_report_filter_figure_countries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_countries ALTER COLUMN id SET DEFAULT nextval('public.report_report_filter_figure_countries_id_seq'::regclass);


--
-- Name: report_report_filter_figure_crises id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_crises ALTER COLUMN id SET DEFAULT nextval('public.report_report_filter_figure_crises_id_seq'::regclass);


--
-- Name: report_report_filter_figure_disaster_categories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_categories ALTER COLUMN id SET DEFAULT nextval('public.report_report_filter_event_disaster_categories_id_seq'::regclass);


--
-- Name: report_report_filter_figure_disaster_sub_categories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_sub_categories ALTER COLUMN id SET DEFAULT nextval('public.report_report_filter_event_disaster_sub_categories_id_seq'::regclass);


--
-- Name: report_report_filter_figure_disaster_sub_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_sub_types ALTER COLUMN id SET DEFAULT nextval('public.report_report_filter_event_disaster_sub_types_id_seq'::regclass);


--
-- Name: report_report_filter_figure_disaster_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_types ALTER COLUMN id SET DEFAULT nextval('public.report_report_filter_event_disaster_types_id_seq'::regclass);


--
-- Name: report_report_filter_figure_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_events ALTER COLUMN id SET DEFAULT nextval('public.report_report_filter_events_id_seq'::regclass);


--
-- Name: report_report_filter_figure_geographical_groups id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_geographical_groups ALTER COLUMN id SET DEFAULT nextval('public.report_report_filter_figure_geographical_groups_id_seq'::regclass);


--
-- Name: report_report_filter_figure_regions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_regions ALTER COLUMN id SET DEFAULT nextval('public.report_report_filter_figure_regions_id_seq'::regclass);


--
-- Name: report_report_filter_figure_sources id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_sources ALTER COLUMN id SET DEFAULT nextval('public.report_report_filter_entry_sources_id_seq'::regclass);


--
-- Name: report_report_filter_figure_tags id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_tags ALTER COLUMN id SET DEFAULT nextval('public.report_report_filter_figure_tags_id_seq'::regclass);


--
-- Name: report_report_filter_figure_violence_sub_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_violence_sub_types ALTER COLUMN id SET DEFAULT nextval('public.report_report_filter_event_violence_sub_types_id_seq'::regclass);


--
-- Name: report_report_filter_figure_violence_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_violence_types ALTER COLUMN id SET DEFAULT nextval('public.report_report_filter_event_violence_types_id_seq'::regclass);


--
-- Name: report_report_reports id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_reports ALTER COLUMN id SET DEFAULT nextval('public.report_report_reports_id_seq'::regclass);


--
-- Name: report_reportapproval id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportapproval ALTER COLUMN id SET DEFAULT nextval('public.report_reportapproval_id_seq'::regclass);


--
-- Name: report_reportcomment id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportcomment ALTER COLUMN id SET DEFAULT nextval('public.report_reportcomment_id_seq'::regclass);


--
-- Name: report_reportgeneration id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportgeneration ALTER COLUMN id SET DEFAULT nextval('public.report_reportgeneration_id_seq'::regclass);


--
-- Name: users_user id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_user ALTER COLUMN id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Name: users_user_groups id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_user_groups ALTER COLUMN id SET DEFAULT nextval('public.users_user_groups_id_seq'::regclass);


--
-- Name: users_user_user_permissions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_user_user_permissions ALTER COLUMN id SET DEFAULT nextval('public.users_user_user_permissions_id_seq'::regclass);


--
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- Name: authtoken_token authtoken_token_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_pkey PRIMARY KEY (key);


--
-- Name: authtoken_token authtoken_token_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_user_id_key UNIQUE (user_id);


--
-- Name: contact_communication contact_communication_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_communication
    ADD CONSTRAINT contact_communication_pkey PRIMARY KEY (id);


--
-- Name: contact_communicationmedium contact_communicationmedium_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_communicationmedium
    ADD CONSTRAINT contact_communicationmedium_pkey PRIMARY KEY (id);


--
-- Name: contact_contact_countries_of_operation contact_contact_countrie_contact_id_country_id_7515023f_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_contact_countries_of_operation
    ADD CONSTRAINT contact_contact_countrie_contact_id_country_id_7515023f_uniq UNIQUE (contact_id, country_id);


--
-- Name: contact_contact_countries_of_operation contact_contact_countries_of_operation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_contact_countries_of_operation
    ADD CONSTRAINT contact_contact_countries_of_operation_pkey PRIMARY KEY (id);


--
-- Name: contact_contact contact_contact_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_contact
    ADD CONSTRAINT contact_contact_pkey PRIMARY KEY (id);


--
-- Name: contextualupdate_contextualupdate_countries contextualupdate_context_contextualupdate_id_coun_8d0804e4_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_countries
    ADD CONSTRAINT contextualupdate_context_contextualupdate_id_coun_8d0804e4_uniq UNIQUE (contextualupdate_id, country_id);


--
-- Name: contextualupdate_contextualupdate_tags contextualupdate_context_contextualupdate_id_figu_af071fb5_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_tags
    ADD CONSTRAINT contextualupdate_context_contextualupdate_id_figu_af071fb5_uniq UNIQUE (contextualupdate_id, figuretag_id);


--
-- Name: contextualupdate_contextualupdate_sources contextualupdate_context_contextualupdate_id_orga_2408f055_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_sources
    ADD CONSTRAINT contextualupdate_context_contextualupdate_id_orga_2408f055_uniq UNIQUE (contextualupdate_id, organization_id);


--
-- Name: contextualupdate_contextualupdate_publishers contextualupdate_context_contextualupdate_id_orga_ee4a7615_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_publishers
    ADD CONSTRAINT contextualupdate_context_contextualupdate_id_orga_ee4a7615_uniq UNIQUE (contextualupdate_id, organization_id);


--
-- Name: contextualupdate_contextualupdate_countries contextualupdate_contextualupdate_countries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_countries
    ADD CONSTRAINT contextualupdate_contextualupdate_countries_pkey PRIMARY KEY (id);


--
-- Name: contextualupdate_contextualupdate contextualupdate_contextualupdate_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate
    ADD CONSTRAINT contextualupdate_contextualupdate_pkey PRIMARY KEY (id);


--
-- Name: contextualupdate_contextualupdate_publishers contextualupdate_contextualupdate_publishers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_publishers
    ADD CONSTRAINT contextualupdate_contextualupdate_publishers_pkey PRIMARY KEY (id);


--
-- Name: contextualupdate_contextualupdate_sources contextualupdate_contextualupdate_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_sources
    ADD CONSTRAINT contextualupdate_contextualupdate_sources_pkey PRIMARY KEY (id);


--
-- Name: contextualupdate_contextualupdate_tags contextualupdate_contextualupdate_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_tags
    ADD CONSTRAINT contextualupdate_contextualupdate_tags_pkey PRIMARY KEY (id);


--
-- Name: contrib_attachment contrib_attachment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_attachment
    ADD CONSTRAINT contrib_attachment_pkey PRIMARY KEY (id);


--
-- Name: contrib_bulkapioperation contrib_bulkapioperation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_bulkapioperation
    ADD CONSTRAINT contrib_bulkapioperation_pkey PRIMARY KEY (id);


--
-- Name: contrib_client contrib_client_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_client
    ADD CONSTRAINT contrib_client_code_key UNIQUE (code);


--
-- Name: contrib_client contrib_client_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_client
    ADD CONSTRAINT contrib_client_pkey PRIMARY KEY (id);


--
-- Name: contrib_clienttrackinfo contrib_clienttrackinfo_client_id_api_type_track_f48d0d77_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_clienttrackinfo
    ADD CONSTRAINT contrib_clienttrackinfo_client_id_api_type_track_f48d0d77_uniq UNIQUE (client_id, api_type, tracked_date);


--
-- Name: contrib_clienttrackinfo contrib_clienttrackinfo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_clienttrackinfo
    ADD CONSTRAINT contrib_clienttrackinfo_pkey PRIMARY KEY (id);


--
-- Name: contrib_exceldownload contrib_exceldownload_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_exceldownload
    ADD CONSTRAINT contrib_exceldownload_pkey PRIMARY KEY (id);


--
-- Name: contrib_sourcepreview contrib_sourcepreview_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_sourcepreview
    ADD CONSTRAINT contrib_sourcepreview_pkey PRIMARY KEY (id);


--
-- Name: country_contextualanalysis country_contextualanalysis_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_contextualanalysis
    ADD CONSTRAINT country_contextualanalysis_pkey PRIMARY KEY (id);


--
-- Name: country_country country_country_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_country
    ADD CONSTRAINT country_country_pkey PRIMARY KEY (id);


--
-- Name: country_countrypopulation country_countrypopulation_country_id_year_ebb634c0_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_countrypopulation
    ADD CONSTRAINT country_countrypopulation_country_id_year_ebb634c0_uniq UNIQUE (country_id, year);


--
-- Name: country_countrypopulation country_countrypopulation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_countrypopulation
    ADD CONSTRAINT country_countrypopulation_pkey PRIMARY KEY (id);


--
-- Name: country_countryregion country_countryregion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_countryregion
    ADD CONSTRAINT country_countryregion_pkey PRIMARY KEY (id);


--
-- Name: country_countrysubregion country_countrysubregion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_countrysubregion
    ADD CONSTRAINT country_countrysubregion_pkey PRIMARY KEY (id);


--
-- Name: country_geographicalgroup country_geographicalgroup_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_geographicalgroup
    ADD CONSTRAINT country_geographicalgroup_pkey PRIMARY KEY (id);


--
-- Name: country_householdsize country_householdsize_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_householdsize
    ADD CONSTRAINT country_householdsize_pkey PRIMARY KEY (id);


--
-- Name: country_monitoringsubregion country_monitoringsubregion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_monitoringsubregion
    ADD CONSTRAINT country_monitoringsubregion_pkey PRIMARY KEY (id);


--
-- Name: country_summary country_summary_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_summary
    ADD CONSTRAINT country_summary_pkey PRIMARY KEY (id);


--
-- Name: crisis_crisis_countries crisis_crisis_countries_crisis_id_country_id_51bde1cb_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crisis_crisis_countries
    ADD CONSTRAINT crisis_crisis_countries_crisis_id_country_id_51bde1cb_uniq UNIQUE (crisis_id, country_id);


--
-- Name: crisis_crisis_countries crisis_crisis_countries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crisis_crisis_countries
    ADD CONSTRAINT crisis_crisis_countries_pkey PRIMARY KEY (id);


--
-- Name: crisis_crisis crisis_crisis_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crisis_crisis
    ADD CONSTRAINT crisis_crisis_pkey PRIMARY KEY (id);


--
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- Name: entry_disaggregatedage entry_disaggregatedage_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_disaggregatedage
    ADD CONSTRAINT entry_disaggregatedage_pkey PRIMARY KEY (id);


--
-- Name: entry_entry entry_entry_associated_parked_item_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entry
    ADD CONSTRAINT entry_entry_associated_parked_item_id_key UNIQUE (associated_parked_item_id);


--
-- Name: entry_entry entry_entry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entry
    ADD CONSTRAINT entry_entry_pkey PRIMARY KEY (id);


--
-- Name: entry_entry_publishers entry_entry_publishers_entry_id_organization_id_4b58b702_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entry_publishers
    ADD CONSTRAINT entry_entry_publishers_entry_id_organization_id_4b58b702_uniq UNIQUE (entry_id, organization_id);


--
-- Name: entry_entry_publishers entry_entry_publishers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entry_publishers
    ADD CONSTRAINT entry_entry_publishers_pkey PRIMARY KEY (id);


--
-- Name: entry_entryreviewer entry_entryreviewer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entryreviewer
    ADD CONSTRAINT entry_entryreviewer_pkey PRIMARY KEY (id);


--
-- Name: entry_externalapidump entry_externalapidump_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_externalapidump
    ADD CONSTRAINT entry_externalapidump_pkey PRIMARY KEY (id);


--
-- Name: entry_figure_context_of_violence entry_figure_context_of__figure_id_contextofviole_ecb49cda_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_context_of_violence
    ADD CONSTRAINT entry_figure_context_of__figure_id_contextofviole_ecb49cda_uniq UNIQUE (figure_id, contextofviolence_id);


--
-- Name: entry_figure_context_of_violence entry_figure_context_of_violence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_context_of_violence
    ADD CONSTRAINT entry_figure_context_of_violence_pkey PRIMARY KEY (id);


--
-- Name: entry_figure_disaggregation_age entry_figure_disaggregat_figure_id_disaggregateda_53025dea_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_disaggregation_age
    ADD CONSTRAINT entry_figure_disaggregat_figure_id_disaggregateda_53025dea_uniq UNIQUE (figure_id, disaggregatedage_id);


--
-- Name: entry_figure_disaggregation_age entry_figure_disaggregation_age_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_disaggregation_age
    ADD CONSTRAINT entry_figure_disaggregation_age_pkey PRIMARY KEY (id);


--
-- Name: entry_figure_geo_locations entry_figure_geo_locations_figure_id_osmname_id_0f8677fb_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_geo_locations
    ADD CONSTRAINT entry_figure_geo_locations_figure_id_osmname_id_0f8677fb_uniq UNIQUE (figure_id, osmname_id);


--
-- Name: entry_figure_geo_locations entry_figure_geo_locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_geo_locations
    ADD CONSTRAINT entry_figure_geo_locations_pkey PRIMARY KEY (id);


--
-- Name: entry_figure entry_figure_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure
    ADD CONSTRAINT entry_figure_pkey PRIMARY KEY (id);


--
-- Name: entry_figure_sources entry_figure_sources_figure_id_organization_id_3cb6d684_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_sources
    ADD CONSTRAINT entry_figure_sources_figure_id_organization_id_3cb6d684_uniq UNIQUE (figure_id, organization_id);


--
-- Name: entry_figure_sources entry_figure_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_sources
    ADD CONSTRAINT entry_figure_sources_pkey PRIMARY KEY (id);


--
-- Name: entry_figure_tags entry_figure_tags_figure_id_figuretag_id_5bb5242b_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_tags
    ADD CONSTRAINT entry_figure_tags_figure_id_figuretag_id_5bb5242b_uniq UNIQUE (figure_id, figuretag_id);


--
-- Name: entry_figure_tags entry_figure_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_tags
    ADD CONSTRAINT entry_figure_tags_pkey PRIMARY KEY (id);


--
-- Name: entry_figuretag entry_figuretag_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figuretag
    ADD CONSTRAINT entry_figuretag_pkey PRIMARY KEY (id);


--
-- Name: entry_osmname entry_osmname_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_osmname
    ADD CONSTRAINT entry_osmname_pkey PRIMARY KEY (id);


--
-- Name: event_actor event_actor_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_actor
    ADD CONSTRAINT event_actor_pkey PRIMARY KEY (id);


--
-- Name: event_contextofviolence event_contextofviolence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_contextofviolence
    ADD CONSTRAINT event_contextofviolence_pkey PRIMARY KEY (id);


--
-- Name: event_disastercategory event_disastercategory_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_disastercategory
    ADD CONSTRAINT event_disastercategory_pkey PRIMARY KEY (id);


--
-- Name: event_disastersubcategory event_disastersubcategory_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_disastersubcategory
    ADD CONSTRAINT event_disastersubcategory_pkey PRIMARY KEY (id);


--
-- Name: event_disastersubtype event_disastersubtype_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_disastersubtype
    ADD CONSTRAINT event_disastersubtype_pkey PRIMARY KEY (id);


--
-- Name: event_disastertype event_disastertype_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_disastertype
    ADD CONSTRAINT event_disastertype_pkey PRIMARY KEY (id);


--
-- Name: event_event_context_of_violence event_event_context_of_v_event_id_contextofviolen_cf5fb605_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event_context_of_violence
    ADD CONSTRAINT event_event_context_of_v_event_id_contextofviolen_cf5fb605_uniq UNIQUE (event_id, contextofviolence_id);


--
-- Name: event_event_context_of_violence event_event_context_of_violence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event_context_of_violence
    ADD CONSTRAINT event_event_context_of_violence_pkey PRIMARY KEY (id);


--
-- Name: event_event_countries event_event_countries_event_id_country_id_6cffb2b2_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event_countries
    ADD CONSTRAINT event_event_countries_event_id_country_id_6cffb2b2_uniq UNIQUE (event_id, country_id);


--
-- Name: event_event_countries event_event_countries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event_countries
    ADD CONSTRAINT event_event_countries_pkey PRIMARY KEY (id);


--
-- Name: event_event event_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event
    ADD CONSTRAINT event_event_pkey PRIMARY KEY (id);


--
-- Name: event_eventcode event_eventcode_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_eventcode
    ADD CONSTRAINT event_eventcode_pkey PRIMARY KEY (id);


--
-- Name: event_eventcode event_eventcode_uuid_a0f0966f_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_eventcode
    ADD CONSTRAINT event_eventcode_uuid_a0f0966f_uniq UNIQUE (uuid);


--
-- Name: event_osvsubtype event_osvsubtype_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_osvsubtype
    ADD CONSTRAINT event_osvsubtype_pkey PRIMARY KEY (id);


--
-- Name: event_othersubtype event_othersubtype_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_othersubtype
    ADD CONSTRAINT event_othersubtype_pkey PRIMARY KEY (id);


--
-- Name: event_violence event_violence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_violence
    ADD CONSTRAINT event_violence_pkey PRIMARY KEY (id);


--
-- Name: event_violencesubtype event_violencesubtype_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_violencesubtype
    ADD CONSTRAINT event_violencesubtype_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery_filter_context_of_violence extraction_extractionque_extractionquery_id_conte_e7eb74ad_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_context_of_violence
    ADD CONSTRAINT extraction_extractionque_extractionquery_id_conte_e7eb74ad_uniq UNIQUE (extractionquery_id, contextofviolence_id);


--
-- Name: extraction_extractionquery_filter_figure_regions extraction_extractionque_extractionquery_id_count_766b4c39_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_regions
    ADD CONSTRAINT extraction_extractionque_extractionquery_id_count_766b4c39_uniq UNIQUE (extractionquery_id, countryregion_id);


--
-- Name: extraction_extractionquery_filter_figure_countries extraction_extractionque_extractionquery_id_count_d01351b5_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_countries
    ADD CONSTRAINT extraction_extractionque_extractionquery_id_count_d01351b5_uniq UNIQUE (extractionquery_id, country_id);


--
-- Name: extraction_extractionquery_filter_figure_crises extraction_extractionque_extractionquery_id_crisi_41ece374_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_crises
    ADD CONSTRAINT extraction_extractionque_extractionquery_id_crisi_41ece374_uniq UNIQUE (extractionquery_id, crisis_id);


--
-- Name: extraction_extractionquery_filter_figure_disaster_types extraction_extractionque_extractionquery_id_disas_1adb8aff_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_types
    ADD CONSTRAINT extraction_extractionque_extractionquery_id_disas_1adb8aff_uniq UNIQUE (extractionquery_id, disastertype_id);


--
-- Name: extraction_extractionquery_filter_figure_disaster_sub_types extraction_extractionque_extractionquery_id_disas_3dc11472_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_sub_types
    ADD CONSTRAINT extraction_extractionque_extractionquery_id_disas_3dc11472_uniq UNIQUE (extractionquery_id, disastersubtype_id);


--
-- Name: extraction_extractionquery_filter_figure_disaster_categories extraction_extractionque_extractionquery_id_disas_5e41f064_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_categories
    ADD CONSTRAINT extraction_extractionque_extractionquery_id_disas_5e41f064_uniq UNIQUE (extractionquery_id, disastercategory_id);


--
-- Name: extraction_extractionquery_filter_figure_disaster_sub_categf349 extraction_extractionque_extractionquery_id_disas_a3e0ff58_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_sub_categf349
    ADD CONSTRAINT extraction_extractionque_extractionquery_id_disas_a3e0ff58_uniq UNIQUE (extractionquery_id, disastersubcategory_id);


--
-- Name: extraction_extractionquery_filter_figure_events extraction_extractionque_extractionquery_id_event_5a2fe05b_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_events
    ADD CONSTRAINT extraction_extractionque_extractionquery_id_event_5a2fe05b_uniq UNIQUE (extractionquery_id, event_id);


--
-- Name: extraction_extractionquery_filter_figure_tags extraction_extractionque_extractionquery_id_figur_4d47a69f_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_tags
    ADD CONSTRAINT extraction_extractionque_extractionquery_id_figur_4d47a69f_uniq UNIQUE (extractionquery_id, figuretag_id);


--
-- Name: extraction_extractionquery_filter_figure_geographical_groups extraction_extractionque_extractionquery_id_geogr_22767eab_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_geographical_groups
    ADD CONSTRAINT extraction_extractionque_extractionquery_id_geogr_22767eab_uniq UNIQUE (extractionquery_id, geographicalgroup_id);


--
-- Name: extraction_extractionquery_filter_figure_sources extraction_extractionque_extractionquery_id_organ_55206a07_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_sources
    ADD CONSTRAINT extraction_extractionque_extractionquery_id_organ_55206a07_uniq UNIQUE (extractionquery_id, organization_id);


--
-- Name: extraction_extractionquery_filter_entry_publishers extraction_extractionque_extractionquery_id_organ_b688938e_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_entry_publishers
    ADD CONSTRAINT extraction_extractionque_extractionquery_id_organ_b688938e_uniq UNIQUE (extractionquery_id, organization_id);


--
-- Name: extraction_extractionquery_filter_created_by extraction_extractionque_extractionquery_id_user__e1cf258a_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_created_by
    ADD CONSTRAINT extraction_extractionque_extractionquery_id_user__e1cf258a_uniq UNIQUE (extractionquery_id, user_id);


--
-- Name: extraction_extractionquery_filter_figure_violence_sub_types extraction_extractionque_extractionquery_id_viole_599d61b2_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_violence_sub_types
    ADD CONSTRAINT extraction_extractionque_extractionquery_id_viole_599d61b2_uniq UNIQUE (extractionquery_id, violencesubtype_id);


--
-- Name: extraction_extractionquery_filter_figure_violence_types extraction_extractionque_extractionquery_id_viole_c66bdfb9_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_violence_types
    ADD CONSTRAINT extraction_extractionque_extractionquery_id_viole_c66bdfb9_uniq UNIQUE (extractionquery_id, violence_id);


--
-- Name: extraction_extractionquery_filter_context_of_violence extraction_extractionquery_filter_context_of_violence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_context_of_violence
    ADD CONSTRAINT extraction_extractionquery_filter_context_of_violence_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery_filter_created_by extraction_extractionquery_filter_entry_created_by_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_created_by
    ADD CONSTRAINT extraction_extractionquery_filter_entry_created_by_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery_filter_entry_publishers extraction_extractionquery_filter_entry_publishers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_entry_publishers
    ADD CONSTRAINT extraction_extractionquery_filter_entry_publishers_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery_filter_figure_sources extraction_extractionquery_filter_entry_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_sources
    ADD CONSTRAINT extraction_extractionquery_filter_entry_sources_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery_filter_figure_disaster_categories extraction_extractionquery_filter_event_disaster_categorie_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_categories
    ADD CONSTRAINT extraction_extractionquery_filter_event_disaster_categorie_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery_filter_figure_disaster_sub_categf349 extraction_extractionquery_filter_event_disaster_sub_categ_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_sub_categf349
    ADD CONSTRAINT extraction_extractionquery_filter_event_disaster_sub_categ_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery_filter_figure_disaster_sub_types extraction_extractionquery_filter_event_disaster_sub_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_sub_types
    ADD CONSTRAINT extraction_extractionquery_filter_event_disaster_sub_types_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery_filter_figure_disaster_types extraction_extractionquery_filter_event_disaster_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_types
    ADD CONSTRAINT extraction_extractionquery_filter_event_disaster_types_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery_filter_figure_violence_sub_types extraction_extractionquery_filter_event_violence_sub_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_violence_sub_types
    ADD CONSTRAINT extraction_extractionquery_filter_event_violence_sub_types_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery_filter_figure_violence_types extraction_extractionquery_filter_event_violence_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_violence_types
    ADD CONSTRAINT extraction_extractionquery_filter_event_violence_types_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery_filter_figure_events extraction_extractionquery_filter_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_events
    ADD CONSTRAINT extraction_extractionquery_filter_events_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery_filter_figure_countries extraction_extractionquery_filter_figure_countries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_countries
    ADD CONSTRAINT extraction_extractionquery_filter_figure_countries_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery_filter_figure_crises extraction_extractionquery_filter_figure_crises_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_crises
    ADD CONSTRAINT extraction_extractionquery_filter_figure_crises_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery_filter_figure_geographical_groups extraction_extractionquery_filter_figure_geographical_grou_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_geographical_groups
    ADD CONSTRAINT extraction_extractionquery_filter_figure_geographical_grou_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery_filter_figure_regions extraction_extractionquery_filter_figure_regions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_regions
    ADD CONSTRAINT extraction_extractionquery_filter_figure_regions_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery_filter_figure_tags extraction_extractionquery_filter_figure_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_tags
    ADD CONSTRAINT extraction_extractionquery_filter_figure_tags_pkey PRIMARY KEY (id);


--
-- Name: extraction_extractionquery extraction_extractionquery_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery
    ADD CONSTRAINT extraction_extractionquery_pkey PRIMARY KEY (id);


--
-- Name: gidd_conflict gidd_conflict_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_conflict
    ADD CONSTRAINT gidd_conflict_pkey PRIMARY KEY (id);


--
-- Name: gidd_conflictlegacy gidd_conflictlegacy_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_conflictlegacy
    ADD CONSTRAINT gidd_conflictlegacy_pkey PRIMARY KEY (id);


--
-- Name: gidd_disaster gidd_disaster_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_disaster
    ADD CONSTRAINT gidd_disaster_pkey PRIMARY KEY (id);


--
-- Name: gidd_disasterlegacy gidd_disasterlegacy_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_disasterlegacy
    ADD CONSTRAINT gidd_disasterlegacy_pkey PRIMARY KEY (id);


--
-- Name: gidd_displacementdata gidd_displacementdata_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_displacementdata
    ADD CONSTRAINT gidd_displacementdata_pkey PRIMARY KEY (id);


--
-- Name: gidd_statuslog gidd_giddlog_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_statuslog
    ADD CONSTRAINT gidd_giddlog_pkey PRIMARY KEY (id);


--
-- Name: gidd_idpssaddestimate gidd_idpssaddestimate_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_idpssaddestimate
    ADD CONSTRAINT gidd_idpssaddestimate_pkey PRIMARY KEY (id);


--
-- Name: gidd_publicfigureanalysis gidd_publicfigureanalysis_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_publicfigureanalysis
    ADD CONSTRAINT gidd_publicfigureanalysis_pkey PRIMARY KEY (id);


--
-- Name: gidd_releasemetadata gidd_releasemetadata_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_releasemetadata
    ADD CONSTRAINT gidd_releasemetadata_pkey PRIMARY KEY (id);


--
-- Name: organization_organization_countries organization_organizatio_organization_id_country__712112a6_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_organization_countries
    ADD CONSTRAINT organization_organizatio_organization_id_country__712112a6_uniq UNIQUE (organization_id, country_id);


--
-- Name: organization_organization_countries organization_organization_countries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_organization_countries
    ADD CONSTRAINT organization_organization_countries_pkey PRIMARY KEY (id);


--
-- Name: organization_organization organization_organization_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_organization
    ADD CONSTRAINT organization_organization_pkey PRIMARY KEY (id);


--
-- Name: organization_organizationkind organization_organizationkind_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_organizationkind
    ADD CONSTRAINT organization_organizationkind_pkey PRIMARY KEY (id);


--
-- Name: parking_lot_parkeditem parking_lot_parkeditem_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parking_lot_parkeditem
    ADD CONSTRAINT parking_lot_parkeditem_pkey PRIMARY KEY (id);


--
-- Name: report_report_disaggregation_age report_report_disaggrega_report_id_disaggregateda_a538c52c_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_disaggregation_age
    ADD CONSTRAINT report_report_disaggrega_report_id_disaggregateda_a538c52c_uniq UNIQUE (report_id, disaggregatedage_id);


--
-- Name: report_report_disaggregation_age report_report_disaggregation_age_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_disaggregation_age
    ADD CONSTRAINT report_report_disaggregation_age_pkey PRIMARY KEY (id);


--
-- Name: report_report_figures report_report_figures_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_figures
    ADD CONSTRAINT report_report_figures_pkey PRIMARY KEY (id);


--
-- Name: report_report_figures report_report_figures_report_id_figure_id_51d6dc41_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_figures
    ADD CONSTRAINT report_report_figures_report_id_figure_id_51d6dc41_uniq UNIQUE (report_id, figure_id);


--
-- Name: report_report_filter_context_of_violence report_report_filter_con_report_id_contextofviole_3ce3a61b_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_context_of_violence
    ADD CONSTRAINT report_report_filter_con_report_id_contextofviole_3ce3a61b_uniq UNIQUE (report_id, contextofviolence_id);


--
-- Name: report_report_filter_context_of_violence report_report_filter_context_of_violence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_context_of_violence
    ADD CONSTRAINT report_report_filter_context_of_violence_pkey PRIMARY KEY (id);


--
-- Name: report_report_filter_figure_sources report_report_filter_ent_report_id_organization_i_49f0855b_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_sources
    ADD CONSTRAINT report_report_filter_ent_report_id_organization_i_49f0855b_uniq UNIQUE (report_id, organization_id);


--
-- Name: report_report_filter_entry_publishers report_report_filter_ent_report_id_organization_i_50fec2f0_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_entry_publishers
    ADD CONSTRAINT report_report_filter_ent_report_id_organization_i_50fec2f0_uniq UNIQUE (report_id, organization_id);


--
-- Name: report_report_filter_created_by report_report_filter_ent_report_id_user_id_3872972d_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_created_by
    ADD CONSTRAINT report_report_filter_ent_report_id_user_id_3872972d_uniq UNIQUE (report_id, user_id);


--
-- Name: report_report_filter_created_by report_report_filter_entry_created_by_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_created_by
    ADD CONSTRAINT report_report_filter_entry_created_by_pkey PRIMARY KEY (id);


--
-- Name: report_report_filter_entry_publishers report_report_filter_entry_publishers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_entry_publishers
    ADD CONSTRAINT report_report_filter_entry_publishers_pkey PRIMARY KEY (id);


--
-- Name: report_report_filter_figure_sources report_report_filter_entry_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_sources
    ADD CONSTRAINT report_report_filter_entry_sources_pkey PRIMARY KEY (id);


--
-- Name: report_report_filter_figure_disaster_categories report_report_filter_eve_report_id_disastercatego_ae8f0c31_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_categories
    ADD CONSTRAINT report_report_filter_eve_report_id_disastercatego_ae8f0c31_uniq UNIQUE (report_id, disastercategory_id);


--
-- Name: report_report_filter_figure_disaster_sub_categories report_report_filter_eve_report_id_disastersubcat_2539fae6_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_sub_categories
    ADD CONSTRAINT report_report_filter_eve_report_id_disastersubcat_2539fae6_uniq UNIQUE (report_id, disastersubcategory_id);


--
-- Name: report_report_filter_figure_disaster_sub_types report_report_filter_eve_report_id_disastersubtyp_c457ac47_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_sub_types
    ADD CONSTRAINT report_report_filter_eve_report_id_disastersubtyp_c457ac47_uniq UNIQUE (report_id, disastersubtype_id);


--
-- Name: report_report_filter_figure_disaster_types report_report_filter_eve_report_id_disastertype_i_c414e950_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_types
    ADD CONSTRAINT report_report_filter_eve_report_id_disastertype_i_c414e950_uniq UNIQUE (report_id, disastertype_id);


--
-- Name: report_report_filter_figure_violence_types report_report_filter_eve_report_id_violence_id_df142aed_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_violence_types
    ADD CONSTRAINT report_report_filter_eve_report_id_violence_id_df142aed_uniq UNIQUE (report_id, violence_id);


--
-- Name: report_report_filter_figure_violence_sub_types report_report_filter_eve_report_id_violencesubtyp_6cf4a111_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_violence_sub_types
    ADD CONSTRAINT report_report_filter_eve_report_id_violencesubtyp_6cf4a111_uniq UNIQUE (report_id, violencesubtype_id);


--
-- Name: report_report_filter_figure_disaster_categories report_report_filter_event_disaster_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_categories
    ADD CONSTRAINT report_report_filter_event_disaster_categories_pkey PRIMARY KEY (id);


--
-- Name: report_report_filter_figure_disaster_sub_categories report_report_filter_event_disaster_sub_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_sub_categories
    ADD CONSTRAINT report_report_filter_event_disaster_sub_categories_pkey PRIMARY KEY (id);


--
-- Name: report_report_filter_figure_disaster_sub_types report_report_filter_event_disaster_sub_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_sub_types
    ADD CONSTRAINT report_report_filter_event_disaster_sub_types_pkey PRIMARY KEY (id);


--
-- Name: report_report_filter_figure_disaster_types report_report_filter_event_disaster_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_types
    ADD CONSTRAINT report_report_filter_event_disaster_types_pkey PRIMARY KEY (id);


--
-- Name: report_report_filter_figure_violence_sub_types report_report_filter_event_violence_sub_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_violence_sub_types
    ADD CONSTRAINT report_report_filter_event_violence_sub_types_pkey PRIMARY KEY (id);


--
-- Name: report_report_filter_figure_violence_types report_report_filter_event_violence_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_violence_types
    ADD CONSTRAINT report_report_filter_event_violence_types_pkey PRIMARY KEY (id);


--
-- Name: report_report_filter_figure_events report_report_filter_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_events
    ADD CONSTRAINT report_report_filter_events_pkey PRIMARY KEY (id);


--
-- Name: report_report_filter_figure_events report_report_filter_events_report_id_event_id_5a135506_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_events
    ADD CONSTRAINT report_report_filter_events_report_id_event_id_5a135506_uniq UNIQUE (report_id, event_id);


--
-- Name: report_report_filter_figure_countries report_report_filter_fig_report_id_country_id_8dfb4e3b_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_countries
    ADD CONSTRAINT report_report_filter_fig_report_id_country_id_8dfb4e3b_uniq UNIQUE (report_id, country_id);


--
-- Name: report_report_filter_figure_regions report_report_filter_fig_report_id_countryregion__a881e744_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_regions
    ADD CONSTRAINT report_report_filter_fig_report_id_countryregion__a881e744_uniq UNIQUE (report_id, countryregion_id);


--
-- Name: report_report_filter_figure_crises report_report_filter_fig_report_id_crisis_id_a70e60c1_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_crises
    ADD CONSTRAINT report_report_filter_fig_report_id_crisis_id_a70e60c1_uniq UNIQUE (report_id, crisis_id);


--
-- Name: report_report_filter_figure_tags report_report_filter_fig_report_id_figuretag_id_577c5abe_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_tags
    ADD CONSTRAINT report_report_filter_fig_report_id_figuretag_id_577c5abe_uniq UNIQUE (report_id, figuretag_id);


--
-- Name: report_report_filter_figure_geographical_groups report_report_filter_fig_report_id_geographicalgr_85935098_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_geographical_groups
    ADD CONSTRAINT report_report_filter_fig_report_id_geographicalgr_85935098_uniq UNIQUE (report_id, geographicalgroup_id);


--
-- Name: report_report_filter_figure_countries report_report_filter_figure_countries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_countries
    ADD CONSTRAINT report_report_filter_figure_countries_pkey PRIMARY KEY (id);


--
-- Name: report_report_filter_figure_crises report_report_filter_figure_crises_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_crises
    ADD CONSTRAINT report_report_filter_figure_crises_pkey PRIMARY KEY (id);


--
-- Name: report_report_filter_figure_geographical_groups report_report_filter_figure_geographical_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_geographical_groups
    ADD CONSTRAINT report_report_filter_figure_geographical_groups_pkey PRIMARY KEY (id);


--
-- Name: report_report_filter_figure_regions report_report_filter_figure_regions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_regions
    ADD CONSTRAINT report_report_filter_figure_regions_pkey PRIMARY KEY (id);


--
-- Name: report_report_filter_figure_tags report_report_filter_figure_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_tags
    ADD CONSTRAINT report_report_filter_figure_tags_pkey PRIMARY KEY (id);


--
-- Name: report_report report_report_gidd_report_year_6dccb152_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report
    ADD CONSTRAINT report_report_gidd_report_year_6dccb152_uniq UNIQUE (gidd_report_year);


--
-- Name: report_report report_report_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report
    ADD CONSTRAINT report_report_pkey PRIMARY KEY (id);


--
-- Name: report_report_reports report_report_reports_from_report_id_to_report_id_acd66fa9_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_reports
    ADD CONSTRAINT report_report_reports_from_report_id_to_report_id_acd66fa9_uniq UNIQUE (from_report_id, to_report_id);


--
-- Name: report_report_reports report_report_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_reports
    ADD CONSTRAINT report_report_reports_pkey PRIMARY KEY (id);


--
-- Name: report_reportapproval report_reportapproval_generation_id_created_by_id_5dc54661_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportapproval
    ADD CONSTRAINT report_reportapproval_generation_id_created_by_id_5dc54661_uniq UNIQUE (generation_id, created_by_id);


--
-- Name: report_reportapproval report_reportapproval_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportapproval
    ADD CONSTRAINT report_reportapproval_pkey PRIMARY KEY (id);


--
-- Name: report_reportcomment report_reportcomment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportcomment
    ADD CONSTRAINT report_reportcomment_pkey PRIMARY KEY (id);


--
-- Name: report_reportgeneration report_reportgeneration_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportgeneration
    ADD CONSTRAINT report_reportgeneration_pkey PRIMARY KEY (id);


--
-- Name: users_user users_user_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_user
    ADD CONSTRAINT users_user_email_key UNIQUE (email);


--
-- Name: users_user_groups users_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_user_groups
    ADD CONSTRAINT users_user_groups_pkey PRIMARY KEY (id);


--
-- Name: users_user_groups users_user_groups_user_id_group_id_b88eab82_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_user_groups
    ADD CONSTRAINT users_user_groups_user_id_group_id_b88eab82_uniq UNIQUE (user_id, group_id);


--
-- Name: users_user users_user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_user
    ADD CONSTRAINT users_user_pkey PRIMARY KEY (id);


--
-- Name: users_user_user_permissions users_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_user_user_permissions
    ADD CONSTRAINT users_user_user_permissions_pkey PRIMARY KEY (id);


--
-- Name: users_user_user_permissions users_user_user_permissions_user_id_permission_id_43338c45_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_user_user_permissions
    ADD CONSTRAINT users_user_user_permissions_user_id_permission_id_43338c45_uniq UNIQUE (user_id, permission_id);


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- Name: authtoken_token_key_10f0b77e_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX authtoken_token_key_10f0b77e_like ON public.authtoken_token USING btree (key varchar_pattern_ops);


--
-- Name: contact_communication_attachment_id_0670c1d2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contact_communication_attachment_id_0670c1d2 ON public.contact_communication USING btree (attachment_id);


--
-- Name: contact_communication_contact_id_695fbebc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contact_communication_contact_id_695fbebc ON public.contact_communication USING btree (contact_id);


--
-- Name: contact_communication_country_id_08f29400; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contact_communication_country_id_08f29400 ON public.contact_communication USING btree (country_id);


--
-- Name: contact_communication_created_by_id_9c140013; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contact_communication_created_by_id_9c140013 ON public.contact_communication USING btree (created_by_id);


--
-- Name: contact_communication_last_modified_by_id_8e662d0a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contact_communication_last_modified_by_id_8e662d0a ON public.contact_communication USING btree (last_modified_by_id);


--
-- Name: contact_communication_medium_id_e2777d8a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contact_communication_medium_id_e2777d8a ON public.contact_communication USING btree (medium_id);


--
-- Name: contact_contact_countries_of_operation_contact_id_29e6698c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contact_contact_countries_of_operation_contact_id_29e6698c ON public.contact_contact_countries_of_operation USING btree (contact_id);


--
-- Name: contact_contact_countries_of_operation_country_id_c04bd5e1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contact_contact_countries_of_operation_country_id_c04bd5e1 ON public.contact_contact_countries_of_operation USING btree (country_id);


--
-- Name: contact_contact_country_id_8c4af7e6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contact_contact_country_id_8c4af7e6 ON public.contact_contact USING btree (country_id);


--
-- Name: contact_contact_created_by_id_cd24de40; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contact_contact_created_by_id_cd24de40 ON public.contact_contact USING btree (created_by_id);


--
-- Name: contact_contact_last_modified_by_id_5247809c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contact_contact_last_modified_by_id_5247809c ON public.contact_contact USING btree (last_modified_by_id);


--
-- Name: contact_contact_organization_id_a859a91a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contact_contact_organization_id_a859a91a ON public.contact_contact USING btree (organization_id);


--
-- Name: contextualupdate_contextua_contextualupdate_id_16ddd486; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contextualupdate_contextua_contextualupdate_id_16ddd486 ON public.contextualupdate_contextualupdate_publishers USING btree (contextualupdate_id);


--
-- Name: contextualupdate_contextua_contextualupdate_id_bd08f7d6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contextualupdate_contextua_contextualupdate_id_bd08f7d6 ON public.contextualupdate_contextualupdate_tags USING btree (contextualupdate_id);


--
-- Name: contextualupdate_contextua_contextualupdate_id_c39e8d0d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contextualupdate_contextua_contextualupdate_id_c39e8d0d ON public.contextualupdate_contextualupdate_countries USING btree (contextualupdate_id);


--
-- Name: contextualupdate_contextua_contextualupdate_id_fe39274a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contextualupdate_contextua_contextualupdate_id_fe39274a ON public.contextualupdate_contextualupdate_sources USING btree (contextualupdate_id);


--
-- Name: contextualupdate_contextua_organization_id_6800cb5d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contextualupdate_contextua_organization_id_6800cb5d ON public.contextualupdate_contextualupdate_publishers USING btree (organization_id);


--
-- Name: contextualupdate_contextua_organization_id_a59556ab; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contextualupdate_contextua_organization_id_a59556ab ON public.contextualupdate_contextualupdate_sources USING btree (organization_id);


--
-- Name: contextualupdate_contextualupdate_countries_country_id_6b4e4138; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contextualupdate_contextualupdate_countries_country_id_6b4e4138 ON public.contextualupdate_contextualupdate_countries USING btree (country_id);


--
-- Name: contextualupdate_contextualupdate_created_by_id_db618e42; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contextualupdate_contextualupdate_created_by_id_db618e42 ON public.contextualupdate_contextualupdate USING btree (created_by_id);


--
-- Name: contextualupdate_contextualupdate_document_id_2360d8d8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contextualupdate_contextualupdate_document_id_2360d8d8 ON public.contextualupdate_contextualupdate USING btree (document_id);


--
-- Name: contextualupdate_contextualupdate_last_modified_by_id_f924dac5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contextualupdate_contextualupdate_last_modified_by_id_f924dac5 ON public.contextualupdate_contextualupdate USING btree (last_modified_by_id);


--
-- Name: contextualupdate_contextualupdate_preview_id_0086d20d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contextualupdate_contextualupdate_preview_id_0086d20d ON public.contextualupdate_contextualupdate USING btree (preview_id);


--
-- Name: contextualupdate_contextualupdate_tags_figuretag_id_6c454b68; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contextualupdate_contextualupdate_tags_figuretag_id_6c454b68 ON public.contextualupdate_contextualupdate_tags USING btree (figuretag_id);


--
-- Name: contrib_attachment_created_by_id_14f49409; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contrib_attachment_created_by_id_14f49409 ON public.contrib_attachment USING btree (created_by_id);


--
-- Name: contrib_attachment_last_modified_by_id_4b0d23a4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contrib_attachment_last_modified_by_id_4b0d23a4 ON public.contrib_attachment USING btree (last_modified_by_id);


--
-- Name: contrib_bulkapioperation_created_by_id_e02d68c3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contrib_bulkapioperation_created_by_id_e02d68c3 ON public.contrib_bulkapioperation USING btree (created_by_id);


--
-- Name: contrib_client_code_e6b09b4b_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contrib_client_code_e6b09b4b_like ON public.contrib_client USING btree (code varchar_pattern_ops);


--
-- Name: contrib_client_created_by_id_93432454; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contrib_client_created_by_id_93432454 ON public.contrib_client USING btree (created_by_id);


--
-- Name: contrib_client_last_modified_by_id_794335e9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contrib_client_last_modified_by_id_794335e9 ON public.contrib_client USING btree (last_modified_by_id);


--
-- Name: contrib_clienttrackinfo_client_id_4d9ba3a7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contrib_clienttrackinfo_client_id_4d9ba3a7 ON public.contrib_clienttrackinfo USING btree (client_id);


--
-- Name: contrib_exceldownload_created_by_id_21e29bf7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contrib_exceldownload_created_by_id_21e29bf7 ON public.contrib_exceldownload USING btree (created_by_id);


--
-- Name: contrib_exceldownload_last_modified_by_id_6601c16e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contrib_exceldownload_last_modified_by_id_6601c16e ON public.contrib_exceldownload USING btree (last_modified_by_id);


--
-- Name: contrib_sourcepreview_created_by_id_8406420c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contrib_sourcepreview_created_by_id_8406420c ON public.contrib_sourcepreview USING btree (created_by_id);


--
-- Name: contrib_sourcepreview_last_modified_by_id_9038a421; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contrib_sourcepreview_last_modified_by_id_9038a421 ON public.contrib_sourcepreview USING btree (last_modified_by_id);


--
-- Name: contrib_sourcepreview_token_6ff1d1bb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contrib_sourcepreview_token_6ff1d1bb ON public.contrib_sourcepreview USING btree (token);


--
-- Name: contrib_sourcepreview_token_6ff1d1bb_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contrib_sourcepreview_token_6ff1d1bb_like ON public.contrib_sourcepreview USING btree (token varchar_pattern_ops);


--
-- Name: country_contextualanalysis_country_id_552125cf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX country_contextualanalysis_country_id_552125cf ON public.country_contextualanalysis USING btree (country_id);


--
-- Name: country_contextualanalysis_created_by_id_cd35d63f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX country_contextualanalysis_created_by_id_cd35d63f ON public.country_contextualanalysis USING btree (created_by_id);


--
-- Name: country_contextualanalysis_last_modified_by_id_98b8fb7d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX country_contextualanalysis_last_modified_by_id_98b8fb7d ON public.country_contextualanalysis USING btree (last_modified_by_id);


--
-- Name: country_country_geographical_group_id_1203f4b4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX country_country_geographical_group_id_1203f4b4 ON public.country_country USING btree (geographical_group_id);


--
-- Name: country_country_monitoring_sub_region_id_948de2ec; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX country_country_monitoring_sub_region_id_948de2ec ON public.country_country USING btree (monitoring_sub_region_id);


--
-- Name: country_country_region_id_209d3573; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX country_country_region_id_209d3573 ON public.country_country USING btree (region_id);


--
-- Name: country_country_sub_region_id_788d7b2d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX country_country_sub_region_id_788d7b2d ON public.country_country USING btree (sub_region_id);


--
-- Name: country_countrypopulation_country_id_f0726376; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX country_countrypopulation_country_id_f0726376 ON public.country_countrypopulation USING btree (country_id);


--
-- Name: country_householdsize_country_id_fc2bc48f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX country_householdsize_country_id_fc2bc48f ON public.country_householdsize USING btree (country_id);


--
-- Name: country_householdsize_created_by_id_db8a376d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX country_householdsize_created_by_id_db8a376d ON public.country_householdsize USING btree (created_by_id);


--
-- Name: country_householdsize_last_modified_by_id_3e818f31; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX country_householdsize_last_modified_by_id_3e818f31 ON public.country_householdsize USING btree (last_modified_by_id);


--
-- Name: country_summary_country_id_e10ef71b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX country_summary_country_id_e10ef71b ON public.country_summary USING btree (country_id);


--
-- Name: country_summary_created_by_id_7db5138c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX country_summary_created_by_id_7db5138c ON public.country_summary USING btree (created_by_id);


--
-- Name: country_summary_last_modified_by_id_47daf889; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX country_summary_last_modified_by_id_47daf889 ON public.country_summary USING btree (last_modified_by_id);


--
-- Name: crisis_crisis_countries_country_id_4ded24de; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX crisis_crisis_countries_country_id_4ded24de ON public.crisis_crisis_countries USING btree (country_id);


--
-- Name: crisis_crisis_countries_crisis_id_fea5eb66; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX crisis_crisis_countries_crisis_id_fea5eb66 ON public.crisis_crisis_countries USING btree (crisis_id);


--
-- Name: crisis_crisis_created_by_id_3c746e2a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX crisis_crisis_created_by_id_3c746e2a ON public.crisis_crisis USING btree (created_by_id);


--
-- Name: crisis_crisis_last_modified_by_id_b0a58689; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX crisis_crisis_last_modified_by_id_b0a58689 ON public.crisis_crisis USING btree (last_modified_by_id);


--
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);


--
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


--
-- Name: entry_entry_created_by_id_77569c61; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_entry_created_by_id_77569c61 ON public.entry_entry USING btree (created_by_id);


--
-- Name: entry_entry_document_id_9a6bf6b4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_entry_document_id_9a6bf6b4 ON public.entry_entry USING btree (document_id);


--
-- Name: entry_entry_last_modified_by_id_c630f81a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_entry_last_modified_by_id_c630f81a ON public.entry_entry USING btree (last_modified_by_id);


--
-- Name: entry_entry_preview_id_14b9561e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_entry_preview_id_14b9561e ON public.entry_entry USING btree (preview_id);


--
-- Name: entry_entry_publishers_entry_id_3487adf9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_entry_publishers_entry_id_3487adf9 ON public.entry_entry_publishers USING btree (entry_id);


--
-- Name: entry_entry_publishers_organization_id_6f00d205; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_entry_publishers_organization_id_6f00d205 ON public.entry_entry_publishers USING btree (organization_id);


--
-- Name: entry_entryreviewer_created_by_id_ba9bab66; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_entryreviewer_created_by_id_ba9bab66 ON public.entry_entryreviewer USING btree (created_by_id);


--
-- Name: entry_entryreviewer_entry_id_6cff7177; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_entryreviewer_entry_id_6cff7177 ON public.entry_entryreviewer USING btree (entry_id);


--
-- Name: entry_entryreviewer_last_modified_by_id_368af04b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_entryreviewer_last_modified_by_id_368af04b ON public.entry_entryreviewer USING btree (last_modified_by_id);


--
-- Name: entry_entryreviewer_reviewer_id_bbf7f8c1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_entryreviewer_reviewer_id_bbf7f8c1 ON public.entry_entryreviewer USING btree (reviewer_id);


--
-- Name: entry_figur_categor_522cc9_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figur_categor_522cc9_idx ON public.entry_figure USING btree (category);


--
-- Name: entry_figur_country_9bbef5_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figur_country_9bbef5_idx ON public.entry_figure USING btree (country_id);


--
-- Name: entry_figur_end_dat_ce6b16_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figur_end_dat_ce6b16_idx ON public.entry_figure USING btree (end_date);


--
-- Name: entry_figur_event_i_576559_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figur_event_i_576559_idx ON public.entry_figure USING btree (event_id);


--
-- Name: entry_figur_role_7d7cda_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figur_role_7d7cda_idx ON public.entry_figure USING btree (role);


--
-- Name: entry_figur_start_d_d1f3ad_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figur_start_d_d1f3ad_idx ON public.entry_figure USING btree (start_date);


--
-- Name: entry_figure_approved_by_id_73c3bd48; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_approved_by_id_73c3bd48 ON public.entry_figure USING btree (approved_by_id);


--
-- Name: entry_figure_context_of_violence_contextofviolence_id_fe916500; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_context_of_violence_contextofviolence_id_fe916500 ON public.entry_figure_context_of_violence USING btree (contextofviolence_id);


--
-- Name: entry_figure_context_of_violence_figure_id_55bc7bbd; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_context_of_violence_figure_id_55bc7bbd ON public.entry_figure_context_of_violence USING btree (figure_id);


--
-- Name: entry_figure_country_id_115e26d0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_country_id_115e26d0 ON public.entry_figure USING btree (country_id);


--
-- Name: entry_figure_created_by_id_f3eb7cb4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_created_by_id_f3eb7cb4 ON public.entry_figure USING btree (created_by_id);


--
-- Name: entry_figure_disaggregation_age_disaggregatedage_id_3b9c772f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_disaggregation_age_disaggregatedage_id_3b9c772f ON public.entry_figure_disaggregation_age USING btree (disaggregatedage_id);


--
-- Name: entry_figure_disaggregation_age_figure_id_09ec405f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_disaggregation_age_figure_id_09ec405f ON public.entry_figure_disaggregation_age USING btree (figure_id);


--
-- Name: entry_figure_disaster_category_id_df45d5e5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_disaster_category_id_df45d5e5 ON public.entry_figure USING btree (disaster_category_id);


--
-- Name: entry_figure_disaster_sub_category_id_eeb8f700; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_disaster_sub_category_id_eeb8f700 ON public.entry_figure USING btree (disaster_sub_category_id);


--
-- Name: entry_figure_disaster_sub_type_id_a3434829; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_disaster_sub_type_id_a3434829 ON public.entry_figure USING btree (disaster_sub_type_id);


--
-- Name: entry_figure_disaster_type_id_7ee1cd45; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_disaster_type_id_7ee1cd45 ON public.entry_figure USING btree (disaster_type_id);


--
-- Name: entry_figure_entry_id_171b902d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_entry_id_171b902d ON public.entry_figure USING btree (entry_id);


--
-- Name: entry_figure_event_id_371af29b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_event_id_371af29b ON public.entry_figure USING btree (event_id);


--
-- Name: entry_figure_geo_locations_figure_id_5a28f49e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_geo_locations_figure_id_5a28f49e ON public.entry_figure_geo_locations USING btree (figure_id);


--
-- Name: entry_figure_geo_locations_osmname_id_22baea80; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_geo_locations_osmname_id_22baea80 ON public.entry_figure_geo_locations USING btree (osmname_id);


--
-- Name: entry_figure_last_modified_by_id_5b75bd7a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_last_modified_by_id_5b75bd7a ON public.entry_figure USING btree (last_modified_by_id);


--
-- Name: entry_figure_osv_sub_type_id_6d0add47; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_osv_sub_type_id_6d0add47 ON public.entry_figure USING btree (osv_sub_type_id);


--
-- Name: entry_figure_other_sub_type_id_2875d4f3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_other_sub_type_id_2875d4f3 ON public.entry_figure USING btree (other_sub_type_id);


--
-- Name: entry_figure_sources_figure_id_17455d84; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_sources_figure_id_17455d84 ON public.entry_figure_sources USING btree (figure_id);


--
-- Name: entry_figure_sources_organization_id_19ef0b93; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_sources_organization_id_19ef0b93 ON public.entry_figure_sources USING btree (organization_id);


--
-- Name: entry_figure_start_date_1902e164; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_start_date_1902e164 ON public.entry_figure USING btree (start_date);


--
-- Name: entry_figure_tags_figure_id_7f1dc185; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_tags_figure_id_7f1dc185 ON public.entry_figure_tags USING btree (figure_id);


--
-- Name: entry_figure_tags_figuretag_id_0e3077ce; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_tags_figuretag_id_0e3077ce ON public.entry_figure_tags USING btree (figuretag_id);


--
-- Name: entry_figure_violence_id_b173b0d2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_violence_id_b173b0d2 ON public.entry_figure USING btree (violence_id);


--
-- Name: entry_figure_violence_sub_type_id_c6ca6764; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figure_violence_sub_type_id_c6ca6764 ON public.entry_figure USING btree (violence_sub_type_id);


--
-- Name: entry_figuretag_created_by_id_064cb72e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figuretag_created_by_id_064cb72e ON public.entry_figuretag USING btree (created_by_id);


--
-- Name: entry_figuretag_last_modified_by_id_510f6299; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX entry_figuretag_last_modified_by_id_510f6299 ON public.entry_figuretag USING btree (last_modified_by_id);


--
-- Name: event_actor_country_id_da38de76; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_actor_country_id_da38de76 ON public.event_actor USING btree (country_id);


--
-- Name: event_actor_created_by_id_34fbc986; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_actor_created_by_id_34fbc986 ON public.event_actor USING btree (created_by_id);


--
-- Name: event_actor_last_modified_by_id_7c6c77ae; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_actor_last_modified_by_id_7c6c77ae ON public.event_actor USING btree (last_modified_by_id);


--
-- Name: event_contextofviolence_created_by_id_52afe3c9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_contextofviolence_created_by_id_52afe3c9 ON public.event_contextofviolence USING btree (created_by_id);


--
-- Name: event_contextofviolence_last_modified_by_id_b1076181; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_contextofviolence_last_modified_by_id_b1076181 ON public.event_contextofviolence USING btree (last_modified_by_id);


--
-- Name: event_disastersubcategory_category_id_58c53dd1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_disastersubcategory_category_id_58c53dd1 ON public.event_disastersubcategory USING btree (category_id);


--
-- Name: event_disastersubtype_type_id_98b65775; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_disastersubtype_type_id_98b65775 ON public.event_disastersubtype USING btree (type_id);


--
-- Name: event_disastertype_disaster_sub_category_id_aaaed465; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_disastertype_disaster_sub_category_id_aaaed465 ON public.event_disastertype USING btree (disaster_sub_category_id);


--
-- Name: event_event_actor_id_d0c16ac0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_actor_id_d0c16ac0 ON public.event_event USING btree (actor_id);


--
-- Name: event_event_assignee_id_73b54160; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_assignee_id_73b54160 ON public.event_event USING btree (assignee_id);


--
-- Name: event_event_assigner_id_771ce422; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_assigner_id_771ce422 ON public.event_event USING btree (assigner_id);


--
-- Name: event_event_context_of_violence_contextofviolence_id_06cf8ec5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_context_of_violence_contextofviolence_id_06cf8ec5 ON public.event_event_context_of_violence USING btree (contextofviolence_id);


--
-- Name: event_event_context_of_violence_event_id_ed32afbb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_context_of_violence_event_id_ed32afbb ON public.event_event_context_of_violence USING btree (event_id);


--
-- Name: event_event_countries_country_id_8af8ffa7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_countries_country_id_8af8ffa7 ON public.event_event_countries USING btree (country_id);


--
-- Name: event_event_countries_event_id_9ecce1df; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_countries_event_id_9ecce1df ON public.event_event_countries USING btree (event_id);


--
-- Name: event_event_created_by_id_81bd5a2f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_created_by_id_81bd5a2f ON public.event_event USING btree (created_by_id);


--
-- Name: event_event_crisis_id_3ea85726; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_crisis_id_3ea85726 ON public.event_event USING btree (crisis_id);


--
-- Name: event_event_disaster_category_id_1791d4f2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_disaster_category_id_1791d4f2 ON public.event_event USING btree (disaster_category_id);


--
-- Name: event_event_disaster_sub_category_id_3da84fb8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_disaster_sub_category_id_3da84fb8 ON public.event_event USING btree (disaster_sub_category_id);


--
-- Name: event_event_disaster_sub_type_id_318c38e6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_disaster_sub_type_id_318c38e6 ON public.event_event USING btree (disaster_sub_type_id);


--
-- Name: event_event_disaster_type_id_c11d1e16; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_disaster_type_id_c11d1e16 ON public.event_event USING btree (disaster_type_id);


--
-- Name: event_event_last_modified_by_id_f4eb646c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_last_modified_by_id_f4eb646c ON public.event_event USING btree (last_modified_by_id);


--
-- Name: event_event_osv_sub_type_id_1a1c1e84; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_osv_sub_type_id_1a1c1e84 ON public.event_event USING btree (osv_sub_type_id);


--
-- Name: event_event_other_sub_type_id_fd92209e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_other_sub_type_id_fd92209e ON public.event_event USING btree (other_sub_type_id);


--
-- Name: event_event_violence_id_d854134d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_violence_id_d854134d ON public.event_event USING btree (violence_id);


--
-- Name: event_event_violence_sub_type_id_3728aada; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_event_violence_sub_type_id_3728aada ON public.event_event USING btree (violence_sub_type_id);


--
-- Name: event_eventcode_country_id_470322b0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_eventcode_country_id_470322b0 ON public.event_eventcode USING btree (country_id);


--
-- Name: event_eventcode_event_id_1c5a1c2e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_eventcode_event_id_1c5a1c2e ON public.event_eventcode USING btree (event_id);


--
-- Name: event_othersubtype_created_by_id_78a132e6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_othersubtype_created_by_id_78a132e6 ON public.event_othersubtype USING btree (created_by_id);


--
-- Name: event_othersubtype_last_modified_by_id_21a4d5c0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_othersubtype_last_modified_by_id_21a4d5c0 ON public.event_othersubtype USING btree (last_modified_by_id);


--
-- Name: event_violencesubtype_violence_id_b86cfa6b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX event_violencesubtype_violence_id_b86cfa6b ON public.event_violencesubtype USING btree (violence_id);


--
-- Name: extraction_extractionquery_contextofviolence_id_c88afe97; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_contextofviolence_id_c88afe97 ON public.extraction_extractionquery_filter_context_of_violence USING btree (contextofviolence_id);


--
-- Name: extraction_extractionquery_country_id_de831d1b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_country_id_de831d1b ON public.extraction_extractionquery_filter_figure_countries USING btree (country_id);


--
-- Name: extraction_extractionquery_countryregion_id_e4823cac; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_countryregion_id_e4823cac ON public.extraction_extractionquery_filter_figure_regions USING btree (countryregion_id);


--
-- Name: extraction_extractionquery_created_by_id_40650114; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_created_by_id_40650114 ON public.extraction_extractionquery USING btree (created_by_id);


--
-- Name: extraction_extractionquery_crisis_id_5c5d0015; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_crisis_id_5c5d0015 ON public.extraction_extractionquery_filter_figure_crises USING btree (crisis_id);


--
-- Name: extraction_extractionquery_disastercategory_id_705e8f6e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_disastercategory_id_705e8f6e ON public.extraction_extractionquery_filter_figure_disaster_categories USING btree (disastercategory_id);


--
-- Name: extraction_extractionquery_disastersubcategory_id_e40bbbae; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_disastersubcategory_id_e40bbbae ON public.extraction_extractionquery_filter_figure_disaster_sub_categf349 USING btree (disastersubcategory_id);


--
-- Name: extraction_extractionquery_disastersubtype_id_0f9e157b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_disastersubtype_id_0f9e157b ON public.extraction_extractionquery_filter_figure_disaster_sub_types USING btree (disastersubtype_id);


--
-- Name: extraction_extractionquery_disastertype_id_8d393a52; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_disastertype_id_8d393a52 ON public.extraction_extractionquery_filter_figure_disaster_types USING btree (disastertype_id);


--
-- Name: extraction_extractionquery_extractionquery_id_0fa99430; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_extractionquery_id_0fa99430 ON public.extraction_extractionquery_filter_context_of_violence USING btree (extractionquery_id);


--
-- Name: extraction_extractionquery_extractionquery_id_133a29f0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_extractionquery_id_133a29f0 ON public.extraction_extractionquery_filter_figure_events USING btree (extractionquery_id);


--
-- Name: extraction_extractionquery_extractionquery_id_1840551b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_extractionquery_id_1840551b ON public.extraction_extractionquery_filter_created_by USING btree (extractionquery_id);


--
-- Name: extraction_extractionquery_extractionquery_id_1a2b13f0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_extractionquery_id_1a2b13f0 ON public.extraction_extractionquery_filter_figure_disaster_types USING btree (extractionquery_id);


--
-- Name: extraction_extractionquery_extractionquery_id_1c714003; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_extractionquery_id_1c714003 ON public.extraction_extractionquery_filter_figure_countries USING btree (extractionquery_id);


--
-- Name: extraction_extractionquery_extractionquery_id_2d0e8e22; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_extractionquery_id_2d0e8e22 ON public.extraction_extractionquery_filter_figure_disaster_categories USING btree (extractionquery_id);


--
-- Name: extraction_extractionquery_extractionquery_id_339f830a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_extractionquery_id_339f830a ON public.extraction_extractionquery_filter_figure_tags USING btree (extractionquery_id);


--
-- Name: extraction_extractionquery_extractionquery_id_4cdab64e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_extractionquery_id_4cdab64e ON public.extraction_extractionquery_filter_figure_regions USING btree (extractionquery_id);


--
-- Name: extraction_extractionquery_extractionquery_id_610db1c7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_extractionquery_id_610db1c7 ON public.extraction_extractionquery_filter_figure_violence_types USING btree (extractionquery_id);


--
-- Name: extraction_extractionquery_extractionquery_id_80a391bd; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_extractionquery_id_80a391bd ON public.extraction_extractionquery_filter_figure_violence_sub_types USING btree (extractionquery_id);


--
-- Name: extraction_extractionquery_extractionquery_id_8114cb87; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_extractionquery_id_8114cb87 ON public.extraction_extractionquery_filter_figure_crises USING btree (extractionquery_id);


--
-- Name: extraction_extractionquery_extractionquery_id_8c281ae5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_extractionquery_id_8c281ae5 ON public.extraction_extractionquery_filter_figure_disaster_sub_categf349 USING btree (extractionquery_id);


--
-- Name: extraction_extractionquery_extractionquery_id_94583074; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_extractionquery_id_94583074 ON public.extraction_extractionquery_filter_figure_sources USING btree (extractionquery_id);


--
-- Name: extraction_extractionquery_extractionquery_id_c42d6079; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_extractionquery_id_c42d6079 ON public.extraction_extractionquery_filter_entry_publishers USING btree (extractionquery_id);


--
-- Name: extraction_extractionquery_extractionquery_id_e6f4ebc4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_extractionquery_id_e6f4ebc4 ON public.extraction_extractionquery_filter_figure_disaster_sub_types USING btree (extractionquery_id);


--
-- Name: extraction_extractionquery_extractionquery_id_f18c8c33; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_extractionquery_id_f18c8c33 ON public.extraction_extractionquery_filter_figure_geographical_groups USING btree (extractionquery_id);


--
-- Name: extraction_extractionquery_figuretag_id_a58317a2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_figuretag_id_a58317a2 ON public.extraction_extractionquery_filter_figure_tags USING btree (figuretag_id);


--
-- Name: extraction_extractionquery_filter_events_event_id_65d93e6f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_filter_events_event_id_65d93e6f ON public.extraction_extractionquery_filter_figure_events USING btree (event_id);


--
-- Name: extraction_extractionquery_geographicalgroup_id_b4943087; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_geographicalgroup_id_b4943087 ON public.extraction_extractionquery_filter_figure_geographical_groups USING btree (geographicalgroup_id);


--
-- Name: extraction_extractionquery_last_modified_by_id_123fcd99; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_last_modified_by_id_123fcd99 ON public.extraction_extractionquery USING btree (last_modified_by_id);


--
-- Name: extraction_extractionquery_organization_id_af782d16; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_organization_id_af782d16 ON public.extraction_extractionquery_filter_entry_publishers USING btree (organization_id);


--
-- Name: extraction_extractionquery_organization_id_f62ecdbf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_organization_id_f62ecdbf ON public.extraction_extractionquery_filter_figure_sources USING btree (organization_id);


--
-- Name: extraction_extractionquery_user_id_6ef3d048; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_user_id_6ef3d048 ON public.extraction_extractionquery_filter_created_by USING btree (user_id);


--
-- Name: extraction_extractionquery_violence_id_80b7e2cd; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_violence_id_80b7e2cd ON public.extraction_extractionquery_filter_figure_violence_types USING btree (violence_id);


--
-- Name: extraction_extractionquery_violencesubtype_id_ffbda7f6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX extraction_extractionquery_violencesubtype_id_ffbda7f6 ON public.extraction_extractionquery_filter_figure_violence_sub_types USING btree (violencesubtype_id);


--
-- Name: gidd_conflict_country_id_65a01812; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gidd_conflict_country_id_65a01812 ON public.gidd_conflict USING btree (country_id);


--
-- Name: gidd_disaster_country_id_6a74f1f0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gidd_disaster_country_id_6a74f1f0 ON public.gidd_disaster USING btree (country_id);


--
-- Name: gidd_disaster_event_id_be43faf5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gidd_disaster_event_id_be43faf5 ON public.gidd_disaster USING btree (event_id);


--
-- Name: gidd_disaster_hazard_category_id_70ee3fdf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gidd_disaster_hazard_category_id_70ee3fdf ON public.gidd_disaster USING btree (hazard_category_id);


--
-- Name: gidd_disaster_hazard_sub_category_id_a907383b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gidd_disaster_hazard_sub_category_id_a907383b ON public.gidd_disaster USING btree (hazard_sub_category_id);


--
-- Name: gidd_disaster_hazard_sub_type_id_fce81d1d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gidd_disaster_hazard_sub_type_id_fce81d1d ON public.gidd_disaster USING btree (hazard_sub_type_id);


--
-- Name: gidd_disaster_hazard_type_id_998ef3d6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gidd_disaster_hazard_type_id_998ef3d6 ON public.gidd_disaster USING btree (hazard_type_id);


--
-- Name: gidd_disasterlegacy_hazard_category_id_9ae617a6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gidd_disasterlegacy_hazard_category_id_9ae617a6 ON public.gidd_disasterlegacy USING btree (hazard_category_id);


--
-- Name: gidd_disasterlegacy_hazard_sub_category_id_46fbef2d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gidd_disasterlegacy_hazard_sub_category_id_46fbef2d ON public.gidd_disasterlegacy USING btree (hazard_sub_category_id);


--
-- Name: gidd_disasterlegacy_hazard_sub_type_id_58ae98d0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gidd_disasterlegacy_hazard_sub_type_id_58ae98d0 ON public.gidd_disasterlegacy USING btree (hazard_sub_type_id);


--
-- Name: gidd_disasterlegacy_hazard_type_id_8428ff53; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gidd_disasterlegacy_hazard_type_id_8428ff53 ON public.gidd_disasterlegacy USING btree (hazard_type_id);


--
-- Name: gidd_displacementdata_country_id_7b9790cf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gidd_displacementdata_country_id_7b9790cf ON public.gidd_displacementdata USING btree (country_id);


--
-- Name: gidd_giddlog_triggered_by_id_86b9687d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gidd_giddlog_triggered_by_id_86b9687d ON public.gidd_statuslog USING btree (triggered_by_id);


--
-- Name: gidd_idpssaddestimate_country_id_1b434d54; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gidd_idpssaddestimate_country_id_1b434d54 ON public.gidd_idpssaddestimate USING btree (country_id);


--
-- Name: gidd_publicfigureanalysis_report_id_5097170f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gidd_publicfigureanalysis_report_id_5097170f ON public.gidd_publicfigureanalysis USING btree (report_id);


--
-- Name: gidd_releasemetadata_modified_by_id_a8ea52b0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gidd_releasemetadata_modified_by_id_a8ea52b0 ON public.gidd_releasemetadata USING btree (modified_by_id);


--
-- Name: organization_organization_countries_country_id_f59fb399; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX organization_organization_countries_country_id_f59fb399 ON public.organization_organization_countries USING btree (country_id);


--
-- Name: organization_organization_countries_organization_id_8753609b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX organization_organization_countries_organization_id_8753609b ON public.organization_organization_countries USING btree (organization_id);


--
-- Name: organization_organization_created_by_id_6558d3a2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX organization_organization_created_by_id_6558d3a2 ON public.organization_organization USING btree (created_by_id);


--
-- Name: organization_organization_last_modified_by_id_f9dff5aa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX organization_organization_last_modified_by_id_f9dff5aa ON public.organization_organization USING btree (last_modified_by_id);


--
-- Name: organization_organization_organization_kind_id_b3a467d8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX organization_organization_organization_kind_id_b3a467d8 ON public.organization_organization USING btree (organization_kind_id);


--
-- Name: organization_organization_parent_id_63fa691e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX organization_organization_parent_id_63fa691e ON public.organization_organization USING btree (parent_id);


--
-- Name: organization_organizationkind_created_by_id_c4590cd9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX organization_organizationkind_created_by_id_c4590cd9 ON public.organization_organizationkind USING btree (created_by_id);


--
-- Name: organization_organizationkind_last_modified_by_id_9bdedef2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX organization_organizationkind_last_modified_by_id_9bdedef2 ON public.organization_organizationkind USING btree (last_modified_by_id);


--
-- Name: parking_lot_parkeditem_assigned_to_id_1b60e1f0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parking_lot_parkeditem_assigned_to_id_1b60e1f0 ON public.parking_lot_parkeditem USING btree (assigned_to_id);


--
-- Name: parking_lot_parkeditem_country_id_f5157092; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parking_lot_parkeditem_country_id_f5157092 ON public.parking_lot_parkeditem USING btree (country_id);


--
-- Name: parking_lot_parkeditem_created_by_id_e1169da1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parking_lot_parkeditem_created_by_id_e1169da1 ON public.parking_lot_parkeditem USING btree (created_by_id);


--
-- Name: parking_lot_parkeditem_last_modified_by_id_28887820; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parking_lot_parkeditem_last_modified_by_id_28887820 ON public.parking_lot_parkeditem USING btree (last_modified_by_id);


--
-- Name: report_report_created_by_id_f0c7de2c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_created_by_id_f0c7de2c ON public.report_report USING btree (created_by_id);


--
-- Name: report_report_disaggregation_age_disaggregatedage_id_416edd6a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_disaggregation_age_disaggregatedage_id_416edd6a ON public.report_report_disaggregation_age USING btree (disaggregatedage_id);


--
-- Name: report_report_disaggregation_age_report_id_f7c6e901; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_disaggregation_age_report_id_f7c6e901 ON public.report_report_disaggregation_age USING btree (report_id);


--
-- Name: report_report_figures_figure_id_5a86d8cc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_figures_figure_id_5a86d8cc ON public.report_report_figures USING btree (figure_id);


--
-- Name: report_report_figures_report_id_ead0575d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_figures_report_id_ead0575d ON public.report_report_figures USING btree (report_id);


--
-- Name: report_report_filter_conte_contextofviolence_id_c86f10d8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_conte_contextofviolence_id_c86f10d8 ON public.report_report_filter_context_of_violence USING btree (contextofviolence_id);


--
-- Name: report_report_filter_context_of_violence_report_id_1f746647; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_context_of_violence_report_id_1f746647 ON public.report_report_filter_context_of_violence USING btree (report_id);


--
-- Name: report_report_filter_entry_created_by_report_id_0f4a4738; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_entry_created_by_report_id_0f4a4738 ON public.report_report_filter_created_by USING btree (report_id);


--
-- Name: report_report_filter_entry_created_by_user_id_63fdd890; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_entry_created_by_user_id_63fdd890 ON public.report_report_filter_created_by USING btree (user_id);


--
-- Name: report_report_filter_entry_publishers_organization_id_2f40c38b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_entry_publishers_organization_id_2f40c38b ON public.report_report_filter_entry_publishers USING btree (organization_id);


--
-- Name: report_report_filter_entry_publishers_report_id_1df6929c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_entry_publishers_report_id_1df6929c ON public.report_report_filter_entry_publishers USING btree (report_id);


--
-- Name: report_report_filter_entry_sources_organization_id_e5400c30; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_entry_sources_organization_id_e5400c30 ON public.report_report_filter_figure_sources USING btree (organization_id);


--
-- Name: report_report_filter_entry_sources_report_id_48d866ca; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_entry_sources_report_id_48d866ca ON public.report_report_filter_figure_sources USING btree (report_id);


--
-- Name: report_report_filter_event_disaster_types_report_id_87c29dd1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_event_disaster_types_report_id_87c29dd1 ON public.report_report_filter_figure_disaster_types USING btree (report_id);


--
-- Name: report_report_filter_event_disastercategory_id_02ee6bf8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_event_disastercategory_id_02ee6bf8 ON public.report_report_filter_figure_disaster_categories USING btree (disastercategory_id);


--
-- Name: report_report_filter_event_disastersubcategory_id_b365fbd0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_event_disastersubcategory_id_b365fbd0 ON public.report_report_filter_figure_disaster_sub_categories USING btree (disastersubcategory_id);


--
-- Name: report_report_filter_event_disastersubtype_id_82177e07; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_event_disastersubtype_id_82177e07 ON public.report_report_filter_figure_disaster_sub_types USING btree (disastersubtype_id);


--
-- Name: report_report_filter_event_disastertype_id_0638bc01; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_event_disastertype_id_0638bc01 ON public.report_report_filter_figure_disaster_types USING btree (disastertype_id);


--
-- Name: report_report_filter_event_report_id_03e7abfa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_event_report_id_03e7abfa ON public.report_report_filter_figure_disaster_categories USING btree (report_id);


--
-- Name: report_report_filter_event_report_id_8559b2cd; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_event_report_id_8559b2cd ON public.report_report_filter_figure_violence_sub_types USING btree (report_id);


--
-- Name: report_report_filter_event_report_id_86c63b32; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_event_report_id_86c63b32 ON public.report_report_filter_figure_disaster_sub_types USING btree (report_id);


--
-- Name: report_report_filter_event_report_id_bd4ecf07; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_event_report_id_bd4ecf07 ON public.report_report_filter_figure_disaster_sub_categories USING btree (report_id);


--
-- Name: report_report_filter_event_violence_types_report_id_86b06e01; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_event_violence_types_report_id_86b06e01 ON public.report_report_filter_figure_violence_types USING btree (report_id);


--
-- Name: report_report_filter_event_violence_types_violence_id_44de2736; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_event_violence_types_violence_id_44de2736 ON public.report_report_filter_figure_violence_types USING btree (violence_id);


--
-- Name: report_report_filter_event_violencesubtype_id_bcbf94ab; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_event_violencesubtype_id_bcbf94ab ON public.report_report_filter_figure_violence_sub_types USING btree (violencesubtype_id);


--
-- Name: report_report_filter_events_event_id_c2698b6d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_events_event_id_c2698b6d ON public.report_report_filter_figure_events USING btree (event_id);


--
-- Name: report_report_filter_events_report_id_69ef966a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_events_report_id_69ef966a ON public.report_report_filter_figure_events USING btree (report_id);


--
-- Name: report_report_filter_figur_geographicalgroup_id_5e8a70dd; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_figur_geographicalgroup_id_5e8a70dd ON public.report_report_filter_figure_geographical_groups USING btree (geographicalgroup_id);


--
-- Name: report_report_filter_figur_report_id_c000ab57; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_figur_report_id_c000ab57 ON public.report_report_filter_figure_geographical_groups USING btree (report_id);


--
-- Name: report_report_filter_figure_countries_country_id_914fddfc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_figure_countries_country_id_914fddfc ON public.report_report_filter_figure_countries USING btree (country_id);


--
-- Name: report_report_filter_figure_countries_report_id_c69fbb8e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_figure_countries_report_id_c69fbb8e ON public.report_report_filter_figure_countries USING btree (report_id);


--
-- Name: report_report_filter_figure_crises_crisis_id_6f38a5b7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_figure_crises_crisis_id_6f38a5b7 ON public.report_report_filter_figure_crises USING btree (crisis_id);


--
-- Name: report_report_filter_figure_crises_report_id_06d4595a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_figure_crises_report_id_06d4595a ON public.report_report_filter_figure_crises USING btree (report_id);


--
-- Name: report_report_filter_figure_regions_countryregion_id_3fc19177; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_figure_regions_countryregion_id_3fc19177 ON public.report_report_filter_figure_regions USING btree (countryregion_id);


--
-- Name: report_report_filter_figure_regions_report_id_bf08d5ab; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_figure_regions_report_id_bf08d5ab ON public.report_report_filter_figure_regions USING btree (report_id);


--
-- Name: report_report_filter_figure_tags_figuretag_id_d7fc29b9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_figure_tags_figuretag_id_d7fc29b9 ON public.report_report_filter_figure_tags USING btree (figuretag_id);


--
-- Name: report_report_filter_figure_tags_report_id_86c5cb7c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_filter_figure_tags_report_id_86c5cb7c ON public.report_report_filter_figure_tags USING btree (report_id);


--
-- Name: report_report_is_signed_off_by_id_24155508; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_is_signed_off_by_id_24155508 ON public.report_report USING btree (is_signed_off_by_id);


--
-- Name: report_report_last_modified_by_id_e7fb27cd; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_last_modified_by_id_e7fb27cd ON public.report_report USING btree (last_modified_by_id);


--
-- Name: report_report_reports_from_report_id_e30c2d0f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_reports_from_report_id_e30c2d0f ON public.report_report_reports USING btree (from_report_id);


--
-- Name: report_report_reports_to_report_id_888f510a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_report_reports_to_report_id_888f510a ON public.report_report_reports USING btree (to_report_id);


--
-- Name: report_reportapproval_created_by_id_cf587a18; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_reportapproval_created_by_id_cf587a18 ON public.report_reportapproval USING btree (created_by_id);


--
-- Name: report_reportapproval_generation_id_95786e9d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_reportapproval_generation_id_95786e9d ON public.report_reportapproval USING btree (generation_id);


--
-- Name: report_reportapproval_last_modified_by_id_a9d9bdb3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_reportapproval_last_modified_by_id_a9d9bdb3 ON public.report_reportapproval USING btree (last_modified_by_id);


--
-- Name: report_reportcomment_created_by_id_a915a051; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_reportcomment_created_by_id_a915a051 ON public.report_reportcomment USING btree (created_by_id);


--
-- Name: report_reportcomment_last_modified_by_id_a4dea5c2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_reportcomment_last_modified_by_id_a4dea5c2 ON public.report_reportcomment USING btree (last_modified_by_id);


--
-- Name: report_reportcomment_report_id_77794c18; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_reportcomment_report_id_77794c18 ON public.report_reportcomment USING btree (report_id);


--
-- Name: report_reportgeneration_created_by_id_44f315e6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_reportgeneration_created_by_id_44f315e6 ON public.report_reportgeneration USING btree (created_by_id);


--
-- Name: report_reportgeneration_is_signed_off_by_id_1f276ab9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_reportgeneration_is_signed_off_by_id_1f276ab9 ON public.report_reportgeneration USING btree (is_signed_off_by_id);


--
-- Name: report_reportgeneration_last_modified_by_id_88cb57c5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_reportgeneration_last_modified_by_id_88cb57c5 ON public.report_reportgeneration USING btree (last_modified_by_id);


--
-- Name: report_reportgeneration_report_id_02edd85d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_reportgeneration_report_id_02edd85d ON public.report_reportgeneration USING btree (report_id);


--
-- Name: users_user_email_243f6e77_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX users_user_email_243f6e77_like ON public.users_user USING btree (email varchar_pattern_ops);


--
-- Name: users_user_groups_group_id_9afc8d0e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX users_user_groups_group_id_9afc8d0e ON public.users_user_groups USING btree (group_id);


--
-- Name: users_user_groups_user_id_5f6f5a90; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX users_user_groups_user_id_5f6f5a90 ON public.users_user_groups USING btree (user_id);


--
-- Name: users_user_user_permissions_permission_id_0b93982e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX users_user_user_permissions_permission_id_0b93982e ON public.users_user_user_permissions USING btree (permission_id);


--
-- Name: users_user_user_permissions_user_id_20aca447; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX users_user_user_permissions_user_id_20aca447 ON public.users_user_user_permissions USING btree (user_id);


--
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: authtoken_token authtoken_token_user_id_35299eff_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_user_id_35299eff_fk_users_user_id FOREIGN KEY (user_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contact_communication contact_communicatio_attachment_id_0670c1d2_fk_contrib_a; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_communication
    ADD CONSTRAINT contact_communicatio_attachment_id_0670c1d2_fk_contrib_a FOREIGN KEY (attachment_id) REFERENCES public.contrib_attachment(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contact_communication contact_communicatio_last_modified_by_id_8e662d0a_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_communication
    ADD CONSTRAINT contact_communicatio_last_modified_by_id_8e662d0a_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contact_communication contact_communicatio_medium_id_e2777d8a_fk_contact_c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_communication
    ADD CONSTRAINT contact_communicatio_medium_id_e2777d8a_fk_contact_c FOREIGN KEY (medium_id) REFERENCES public.contact_communicationmedium(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contact_communication contact_communication_contact_id_695fbebc_fk_contact_contact_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_communication
    ADD CONSTRAINT contact_communication_contact_id_695fbebc_fk_contact_contact_id FOREIGN KEY (contact_id) REFERENCES public.contact_contact(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contact_communication contact_communication_country_id_08f29400_fk_country_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_communication
    ADD CONSTRAINT contact_communication_country_id_08f29400_fk_country_country_id FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contact_communication contact_communication_created_by_id_9c140013_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_communication
    ADD CONSTRAINT contact_communication_created_by_id_9c140013_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contact_contact_countries_of_operation contact_contact_coun_contact_id_29e6698c_fk_contact_c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_contact_countries_of_operation
    ADD CONSTRAINT contact_contact_coun_contact_id_29e6698c_fk_contact_c FOREIGN KEY (contact_id) REFERENCES public.contact_contact(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contact_contact_countries_of_operation contact_contact_coun_country_id_c04bd5e1_fk_country_c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_contact_countries_of_operation
    ADD CONSTRAINT contact_contact_coun_country_id_c04bd5e1_fk_country_c FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contact_contact contact_contact_country_id_8c4af7e6_fk_country_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_contact
    ADD CONSTRAINT contact_contact_country_id_8c4af7e6_fk_country_country_id FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contact_contact contact_contact_created_by_id_cd24de40_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_contact
    ADD CONSTRAINT contact_contact_created_by_id_cd24de40_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contact_contact contact_contact_last_modified_by_id_5247809c_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_contact
    ADD CONSTRAINT contact_contact_last_modified_by_id_5247809c_fk_users_user_id FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contact_contact contact_contact_organization_id_a859a91a_fk_organizat; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_contact
    ADD CONSTRAINT contact_contact_organization_id_a859a91a_fk_organizat FOREIGN KEY (organization_id) REFERENCES public.organization_organization(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contextualupdate_contextualupdate_publishers contextualupdate_con_contextualupdate_id_16ddd486_fk_contextua; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_publishers
    ADD CONSTRAINT contextualupdate_con_contextualupdate_id_16ddd486_fk_contextua FOREIGN KEY (contextualupdate_id) REFERENCES public.contextualupdate_contextualupdate(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contextualupdate_contextualupdate_tags contextualupdate_con_contextualupdate_id_bd08f7d6_fk_contextua; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_tags
    ADD CONSTRAINT contextualupdate_con_contextualupdate_id_bd08f7d6_fk_contextua FOREIGN KEY (contextualupdate_id) REFERENCES public.contextualupdate_contextualupdate(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contextualupdate_contextualupdate_countries contextualupdate_con_contextualupdate_id_c39e8d0d_fk_contextua; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_countries
    ADD CONSTRAINT contextualupdate_con_contextualupdate_id_c39e8d0d_fk_contextua FOREIGN KEY (contextualupdate_id) REFERENCES public.contextualupdate_contextualupdate(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contextualupdate_contextualupdate_sources contextualupdate_con_contextualupdate_id_fe39274a_fk_contextua; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_sources
    ADD CONSTRAINT contextualupdate_con_contextualupdate_id_fe39274a_fk_contextua FOREIGN KEY (contextualupdate_id) REFERENCES public.contextualupdate_contextualupdate(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contextualupdate_contextualupdate_countries contextualupdate_con_country_id_6b4e4138_fk_country_c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_countries
    ADD CONSTRAINT contextualupdate_con_country_id_6b4e4138_fk_country_c FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contextualupdate_contextualupdate contextualupdate_con_created_by_id_db618e42_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate
    ADD CONSTRAINT contextualupdate_con_created_by_id_db618e42_fk_users_use FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contextualupdate_contextualupdate contextualupdate_con_document_id_2360d8d8_fk_contrib_a; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate
    ADD CONSTRAINT contextualupdate_con_document_id_2360d8d8_fk_contrib_a FOREIGN KEY (document_id) REFERENCES public.contrib_attachment(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contextualupdate_contextualupdate_tags contextualupdate_con_figuretag_id_6c454b68_fk_entry_fig; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_tags
    ADD CONSTRAINT contextualupdate_con_figuretag_id_6c454b68_fk_entry_fig FOREIGN KEY (figuretag_id) REFERENCES public.entry_figuretag(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contextualupdate_contextualupdate contextualupdate_con_last_modified_by_id_f924dac5_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate
    ADD CONSTRAINT contextualupdate_con_last_modified_by_id_f924dac5_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contextualupdate_contextualupdate_publishers contextualupdate_con_organization_id_6800cb5d_fk_organizat; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_publishers
    ADD CONSTRAINT contextualupdate_con_organization_id_6800cb5d_fk_organizat FOREIGN KEY (organization_id) REFERENCES public.organization_organization(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contextualupdate_contextualupdate_sources contextualupdate_con_organization_id_a59556ab_fk_organizat; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate_sources
    ADD CONSTRAINT contextualupdate_con_organization_id_a59556ab_fk_organizat FOREIGN KEY (organization_id) REFERENCES public.organization_organization(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contextualupdate_contextualupdate contextualupdate_con_preview_id_0086d20d_fk_contrib_s; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contextualupdate_contextualupdate
    ADD CONSTRAINT contextualupdate_con_preview_id_0086d20d_fk_contrib_s FOREIGN KEY (preview_id) REFERENCES public.contrib_sourcepreview(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contrib_attachment contrib_attachment_created_by_id_14f49409_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_attachment
    ADD CONSTRAINT contrib_attachment_created_by_id_14f49409_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contrib_attachment contrib_attachment_last_modified_by_id_4b0d23a4_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_attachment
    ADD CONSTRAINT contrib_attachment_last_modified_by_id_4b0d23a4_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contrib_bulkapioperation contrib_bulkapiopera_created_by_id_e02d68c3_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_bulkapioperation
    ADD CONSTRAINT contrib_bulkapiopera_created_by_id_e02d68c3_fk_users_use FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contrib_client contrib_client_created_by_id_93432454_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_client
    ADD CONSTRAINT contrib_client_created_by_id_93432454_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contrib_client contrib_client_last_modified_by_id_794335e9_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_client
    ADD CONSTRAINT contrib_client_last_modified_by_id_794335e9_fk_users_user_id FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contrib_clienttrackinfo contrib_clienttrackinfo_client_id_4d9ba3a7_fk_contrib_client_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_clienttrackinfo
    ADD CONSTRAINT contrib_clienttrackinfo_client_id_4d9ba3a7_fk_contrib_client_id FOREIGN KEY (client_id) REFERENCES public.contrib_client(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contrib_exceldownload contrib_exceldownloa_last_modified_by_id_6601c16e_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_exceldownload
    ADD CONSTRAINT contrib_exceldownloa_last_modified_by_id_6601c16e_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contrib_exceldownload contrib_exceldownload_created_by_id_21e29bf7_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_exceldownload
    ADD CONSTRAINT contrib_exceldownload_created_by_id_21e29bf7_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contrib_sourcepreview contrib_sourceprevie_last_modified_by_id_9038a421_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_sourcepreview
    ADD CONSTRAINT contrib_sourceprevie_last_modified_by_id_9038a421_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: contrib_sourcepreview contrib_sourcepreview_created_by_id_8406420c_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrib_sourcepreview
    ADD CONSTRAINT contrib_sourcepreview_created_by_id_8406420c_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: country_contextualanalysis country_contextualan_country_id_552125cf_fk_country_c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_contextualanalysis
    ADD CONSTRAINT country_contextualan_country_id_552125cf_fk_country_c FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: country_contextualanalysis country_contextualan_created_by_id_cd35d63f_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_contextualanalysis
    ADD CONSTRAINT country_contextualan_created_by_id_cd35d63f_fk_users_use FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: country_contextualanalysis country_contextualan_last_modified_by_id_98b8fb7d_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_contextualanalysis
    ADD CONSTRAINT country_contextualan_last_modified_by_id_98b8fb7d_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: country_country country_country_geographical_group_i_1203f4b4_fk_country_g; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_country
    ADD CONSTRAINT country_country_geographical_group_i_1203f4b4_fk_country_g FOREIGN KEY (geographical_group_id) REFERENCES public.country_geographicalgroup(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: country_country country_country_monitoring_sub_regio_948de2ec_fk_country_m; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_country
    ADD CONSTRAINT country_country_monitoring_sub_regio_948de2ec_fk_country_m FOREIGN KEY (monitoring_sub_region_id) REFERENCES public.country_monitoringsubregion(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: country_country country_country_region_id_209d3573_fk_country_countryregion_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_country
    ADD CONSTRAINT country_country_region_id_209d3573_fk_country_countryregion_id FOREIGN KEY (region_id) REFERENCES public.country_countryregion(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: country_country country_country_sub_region_id_788d7b2d_fk_country_c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_country
    ADD CONSTRAINT country_country_sub_region_id_788d7b2d_fk_country_c FOREIGN KEY (sub_region_id) REFERENCES public.country_countrysubregion(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: country_countrypopulation country_countrypopul_country_id_f0726376_fk_country_c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_countrypopulation
    ADD CONSTRAINT country_countrypopul_country_id_f0726376_fk_country_c FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: country_householdsize country_householdsiz_last_modified_by_id_3e818f31_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_householdsize
    ADD CONSTRAINT country_householdsiz_last_modified_by_id_3e818f31_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: country_householdsize country_householdsize_country_id_fc2bc48f_fk_country_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_householdsize
    ADD CONSTRAINT country_householdsize_country_id_fc2bc48f_fk_country_country_id FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: country_householdsize country_householdsize_created_by_id_db8a376d_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_householdsize
    ADD CONSTRAINT country_householdsize_created_by_id_db8a376d_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: country_summary country_summary_country_id_e10ef71b_fk_country_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_summary
    ADD CONSTRAINT country_summary_country_id_e10ef71b_fk_country_country_id FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: country_summary country_summary_created_by_id_7db5138c_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_summary
    ADD CONSTRAINT country_summary_created_by_id_7db5138c_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: country_summary country_summary_last_modified_by_id_47daf889_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_summary
    ADD CONSTRAINT country_summary_last_modified_by_id_47daf889_fk_users_user_id FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: crisis_crisis_countries crisis_crisis_countr_country_id_4ded24de_fk_country_c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crisis_crisis_countries
    ADD CONSTRAINT crisis_crisis_countr_country_id_4ded24de_fk_country_c FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: crisis_crisis_countries crisis_crisis_countries_crisis_id_fea5eb66_fk_crisis_crisis_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crisis_crisis_countries
    ADD CONSTRAINT crisis_crisis_countries_crisis_id_fea5eb66_fk_crisis_crisis_id FOREIGN KEY (crisis_id) REFERENCES public.crisis_crisis(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: crisis_crisis crisis_crisis_created_by_id_3c746e2a_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crisis_crisis
    ADD CONSTRAINT crisis_crisis_created_by_id_3c746e2a_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: crisis_crisis crisis_crisis_last_modified_by_id_b0a58689_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crisis_crisis
    ADD CONSTRAINT crisis_crisis_last_modified_by_id_b0a58689_fk_users_user_id FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_users_user_id FOREIGN KEY (user_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_entry entry_entry_associated_parked_it_bffa02ae_fk_parking_l; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entry
    ADD CONSTRAINT entry_entry_associated_parked_it_bffa02ae_fk_parking_l FOREIGN KEY (associated_parked_item_id) REFERENCES public.parking_lot_parkeditem(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_entry entry_entry_created_by_id_77569c61_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entry
    ADD CONSTRAINT entry_entry_created_by_id_77569c61_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_entry entry_entry_document_id_9a6bf6b4_fk_contrib_attachment_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entry
    ADD CONSTRAINT entry_entry_document_id_9a6bf6b4_fk_contrib_attachment_id FOREIGN KEY (document_id) REFERENCES public.contrib_attachment(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_entry entry_entry_last_modified_by_id_c630f81a_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entry
    ADD CONSTRAINT entry_entry_last_modified_by_id_c630f81a_fk_users_user_id FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_entry entry_entry_preview_id_14b9561e_fk_contrib_sourcepreview_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entry
    ADD CONSTRAINT entry_entry_preview_id_14b9561e_fk_contrib_sourcepreview_id FOREIGN KEY (preview_id) REFERENCES public.contrib_sourcepreview(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_entry_publishers entry_entry_publishe_organization_id_6f00d205_fk_organizat; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entry_publishers
    ADD CONSTRAINT entry_entry_publishe_organization_id_6f00d205_fk_organizat FOREIGN KEY (organization_id) REFERENCES public.organization_organization(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_entry_publishers entry_entry_publishers_entry_id_3487adf9_fk_entry_entry_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entry_publishers
    ADD CONSTRAINT entry_entry_publishers_entry_id_3487adf9_fk_entry_entry_id FOREIGN KEY (entry_id) REFERENCES public.entry_entry(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_entryreviewer entry_entryreviewer_created_by_id_ba9bab66_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entryreviewer
    ADD CONSTRAINT entry_entryreviewer_created_by_id_ba9bab66_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_entryreviewer entry_entryreviewer_entry_id_6cff7177_fk_entry_entry_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entryreviewer
    ADD CONSTRAINT entry_entryreviewer_entry_id_6cff7177_fk_entry_entry_id FOREIGN KEY (entry_id) REFERENCES public.entry_entry(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_entryreviewer entry_entryreviewer_last_modified_by_id_368af04b_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entryreviewer
    ADD CONSTRAINT entry_entryreviewer_last_modified_by_id_368af04b_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_entryreviewer entry_entryreviewer_reviewer_id_bbf7f8c1_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_entryreviewer
    ADD CONSTRAINT entry_entryreviewer_reviewer_id_bbf7f8c1_fk_users_user_id FOREIGN KEY (reviewer_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure entry_figure_approved_by_id_73c3bd48_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure
    ADD CONSTRAINT entry_figure_approved_by_id_73c3bd48_fk_users_user_id FOREIGN KEY (approved_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure_context_of_violence entry_figure_context_contextofviolence_id_fe916500_fk_event_con; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_context_of_violence
    ADD CONSTRAINT entry_figure_context_contextofviolence_id_fe916500_fk_event_con FOREIGN KEY (contextofviolence_id) REFERENCES public.event_contextofviolence(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure_context_of_violence entry_figure_context_figure_id_55bc7bbd_fk_entry_fig; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_context_of_violence
    ADD CONSTRAINT entry_figure_context_figure_id_55bc7bbd_fk_entry_fig FOREIGN KEY (figure_id) REFERENCES public.entry_figure(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure entry_figure_country_id_115e26d0_fk_country_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure
    ADD CONSTRAINT entry_figure_country_id_115e26d0_fk_country_country_id FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure entry_figure_created_by_id_f3eb7cb4_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure
    ADD CONSTRAINT entry_figure_created_by_id_f3eb7cb4_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure_disaggregation_age entry_figure_disaggr_disaggregatedage_id_3b9c772f_fk_entry_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_disaggregation_age
    ADD CONSTRAINT entry_figure_disaggr_disaggregatedage_id_3b9c772f_fk_entry_dis FOREIGN KEY (disaggregatedage_id) REFERENCES public.entry_disaggregatedage(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure_disaggregation_age entry_figure_disaggr_figure_id_09ec405f_fk_entry_fig; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_disaggregation_age
    ADD CONSTRAINT entry_figure_disaggr_figure_id_09ec405f_fk_entry_fig FOREIGN KEY (figure_id) REFERENCES public.entry_figure(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure entry_figure_disaster_category_id_df45d5e5_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure
    ADD CONSTRAINT entry_figure_disaster_category_id_df45d5e5_fk_event_dis FOREIGN KEY (disaster_category_id) REFERENCES public.event_disastercategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure entry_figure_disaster_sub_categor_eeb8f700_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure
    ADD CONSTRAINT entry_figure_disaster_sub_categor_eeb8f700_fk_event_dis FOREIGN KEY (disaster_sub_category_id) REFERENCES public.event_disastersubcategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure entry_figure_disaster_sub_type_id_a3434829_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure
    ADD CONSTRAINT entry_figure_disaster_sub_type_id_a3434829_fk_event_dis FOREIGN KEY (disaster_sub_type_id) REFERENCES public.event_disastersubtype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure entry_figure_disaster_type_id_7ee1cd45_fk_event_disastertype_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure
    ADD CONSTRAINT entry_figure_disaster_type_id_7ee1cd45_fk_event_disastertype_id FOREIGN KEY (disaster_type_id) REFERENCES public.event_disastertype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure entry_figure_entry_id_171b902d_fk_entry_entry_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure
    ADD CONSTRAINT entry_figure_entry_id_171b902d_fk_entry_entry_id FOREIGN KEY (entry_id) REFERENCES public.entry_entry(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure entry_figure_event_id_371af29b_fk_event_event_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure
    ADD CONSTRAINT entry_figure_event_id_371af29b_fk_event_event_id FOREIGN KEY (event_id) REFERENCES public.event_event(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure_geo_locations entry_figure_geo_loc_figure_id_5a28f49e_fk_entry_fig; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_geo_locations
    ADD CONSTRAINT entry_figure_geo_loc_figure_id_5a28f49e_fk_entry_fig FOREIGN KEY (figure_id) REFERENCES public.entry_figure(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure_geo_locations entry_figure_geo_loc_osmname_id_22baea80_fk_entry_osm; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_geo_locations
    ADD CONSTRAINT entry_figure_geo_loc_osmname_id_22baea80_fk_entry_osm FOREIGN KEY (osmname_id) REFERENCES public.entry_osmname(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure entry_figure_last_modified_by_id_5b75bd7a_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure
    ADD CONSTRAINT entry_figure_last_modified_by_id_5b75bd7a_fk_users_user_id FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure entry_figure_osv_sub_type_id_6d0add47_fk_event_osvsubtype_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure
    ADD CONSTRAINT entry_figure_osv_sub_type_id_6d0add47_fk_event_osvsubtype_id FOREIGN KEY (osv_sub_type_id) REFERENCES public.event_osvsubtype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure entry_figure_other_sub_type_id_2875d4f3_fk_event_oth; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure
    ADD CONSTRAINT entry_figure_other_sub_type_id_2875d4f3_fk_event_oth FOREIGN KEY (other_sub_type_id) REFERENCES public.event_othersubtype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure_sources entry_figure_sources_figure_id_17455d84_fk_entry_figure_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_sources
    ADD CONSTRAINT entry_figure_sources_figure_id_17455d84_fk_entry_figure_id FOREIGN KEY (figure_id) REFERENCES public.entry_figure(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure_sources entry_figure_sources_organization_id_19ef0b93_fk_organizat; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_sources
    ADD CONSTRAINT entry_figure_sources_organization_id_19ef0b93_fk_organizat FOREIGN KEY (organization_id) REFERENCES public.organization_organization(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure_tags entry_figure_tags_figure_id_7f1dc185_fk_entry_figure_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_tags
    ADD CONSTRAINT entry_figure_tags_figure_id_7f1dc185_fk_entry_figure_id FOREIGN KEY (figure_id) REFERENCES public.entry_figure(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure_tags entry_figure_tags_figuretag_id_0e3077ce_fk_entry_figuretag_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure_tags
    ADD CONSTRAINT entry_figure_tags_figuretag_id_0e3077ce_fk_entry_figuretag_id FOREIGN KEY (figuretag_id) REFERENCES public.entry_figuretag(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure entry_figure_violence_id_b173b0d2_fk_event_violence_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure
    ADD CONSTRAINT entry_figure_violence_id_b173b0d2_fk_event_violence_id FOREIGN KEY (violence_id) REFERENCES public.event_violence(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figure entry_figure_violence_sub_type_id_c6ca6764_fk_event_vio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figure
    ADD CONSTRAINT entry_figure_violence_sub_type_id_c6ca6764_fk_event_vio FOREIGN KEY (violence_sub_type_id) REFERENCES public.event_violencesubtype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figuretag entry_figuretag_created_by_id_064cb72e_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figuretag
    ADD CONSTRAINT entry_figuretag_created_by_id_064cb72e_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: entry_figuretag entry_figuretag_last_modified_by_id_510f6299_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entry_figuretag
    ADD CONSTRAINT entry_figuretag_last_modified_by_id_510f6299_fk_users_user_id FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_actor event_actor_country_id_da38de76_fk_country_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_actor
    ADD CONSTRAINT event_actor_country_id_da38de76_fk_country_country_id FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_actor event_actor_created_by_id_34fbc986_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_actor
    ADD CONSTRAINT event_actor_created_by_id_34fbc986_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_actor event_actor_last_modified_by_id_7c6c77ae_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_actor
    ADD CONSTRAINT event_actor_last_modified_by_id_7c6c77ae_fk_users_user_id FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_contextofviolence event_contextofviole_last_modified_by_id_b1076181_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_contextofviolence
    ADD CONSTRAINT event_contextofviole_last_modified_by_id_b1076181_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_contextofviolence event_contextofviolence_created_by_id_52afe3c9_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_contextofviolence
    ADD CONSTRAINT event_contextofviolence_created_by_id_52afe3c9_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_disastersubcategory event_disastersubcat_category_id_58c53dd1_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_disastersubcategory
    ADD CONSTRAINT event_disastersubcat_category_id_58c53dd1_fk_event_dis FOREIGN KEY (category_id) REFERENCES public.event_disastercategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_disastersubtype event_disastersubtype_type_id_98b65775_fk_event_disastertype_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_disastersubtype
    ADD CONSTRAINT event_disastersubtype_type_id_98b65775_fk_event_disastertype_id FOREIGN KEY (type_id) REFERENCES public.event_disastertype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_disastertype event_disastertype_disaster_sub_categor_aaaed465_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_disastertype
    ADD CONSTRAINT event_disastertype_disaster_sub_categor_aaaed465_fk_event_dis FOREIGN KEY (disaster_sub_category_id) REFERENCES public.event_disastersubcategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event event_event_actor_id_d0c16ac0_fk_event_actor_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event
    ADD CONSTRAINT event_event_actor_id_d0c16ac0_fk_event_actor_id FOREIGN KEY (actor_id) REFERENCES public.event_actor(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event event_event_assignee_id_73b54160_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event
    ADD CONSTRAINT event_event_assignee_id_73b54160_fk_users_user_id FOREIGN KEY (assignee_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event event_event_assigner_id_771ce422_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event
    ADD CONSTRAINT event_event_assigner_id_771ce422_fk_users_user_id FOREIGN KEY (assigner_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event_context_of_violence event_event_context__contextofviolence_id_06cf8ec5_fk_event_con; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event_context_of_violence
    ADD CONSTRAINT event_event_context__contextofviolence_id_06cf8ec5_fk_event_con FOREIGN KEY (contextofviolence_id) REFERENCES public.event_contextofviolence(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event_context_of_violence event_event_context__event_id_ed32afbb_fk_event_eve; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event_context_of_violence
    ADD CONSTRAINT event_event_context__event_id_ed32afbb_fk_event_eve FOREIGN KEY (event_id) REFERENCES public.event_event(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event_countries event_event_countries_country_id_8af8ffa7_fk_country_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event_countries
    ADD CONSTRAINT event_event_countries_country_id_8af8ffa7_fk_country_country_id FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event_countries event_event_countries_event_id_9ecce1df_fk_event_event_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event_countries
    ADD CONSTRAINT event_event_countries_event_id_9ecce1df_fk_event_event_id FOREIGN KEY (event_id) REFERENCES public.event_event(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event event_event_created_by_id_81bd5a2f_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event
    ADD CONSTRAINT event_event_created_by_id_81bd5a2f_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event event_event_crisis_id_3ea85726_fk_crisis_crisis_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event
    ADD CONSTRAINT event_event_crisis_id_3ea85726_fk_crisis_crisis_id FOREIGN KEY (crisis_id) REFERENCES public.crisis_crisis(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event event_event_disaster_category_id_1791d4f2_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event
    ADD CONSTRAINT event_event_disaster_category_id_1791d4f2_fk_event_dis FOREIGN KEY (disaster_category_id) REFERENCES public.event_disastercategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event event_event_disaster_sub_categor_3da84fb8_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event
    ADD CONSTRAINT event_event_disaster_sub_categor_3da84fb8_fk_event_dis FOREIGN KEY (disaster_sub_category_id) REFERENCES public.event_disastersubcategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event event_event_disaster_sub_type_id_318c38e6_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event
    ADD CONSTRAINT event_event_disaster_sub_type_id_318c38e6_fk_event_dis FOREIGN KEY (disaster_sub_type_id) REFERENCES public.event_disastersubtype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event event_event_disaster_type_id_c11d1e16_fk_event_disastertype_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event
    ADD CONSTRAINT event_event_disaster_type_id_c11d1e16_fk_event_disastertype_id FOREIGN KEY (disaster_type_id) REFERENCES public.event_disastertype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event event_event_last_modified_by_id_f4eb646c_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event
    ADD CONSTRAINT event_event_last_modified_by_id_f4eb646c_fk_users_user_id FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event event_event_osv_sub_type_id_1a1c1e84_fk_event_osvsubtype_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event
    ADD CONSTRAINT event_event_osv_sub_type_id_1a1c1e84_fk_event_osvsubtype_id FOREIGN KEY (osv_sub_type_id) REFERENCES public.event_osvsubtype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event event_event_other_sub_type_id_fd92209e_fk_event_othersubtype_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event
    ADD CONSTRAINT event_event_other_sub_type_id_fd92209e_fk_event_othersubtype_id FOREIGN KEY (other_sub_type_id) REFERENCES public.event_othersubtype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event event_event_violence_id_d854134d_fk_event_violence_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event
    ADD CONSTRAINT event_event_violence_id_d854134d_fk_event_violence_id FOREIGN KEY (violence_id) REFERENCES public.event_violence(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_event event_event_violence_sub_type_id_3728aada_fk_event_vio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_event
    ADD CONSTRAINT event_event_violence_sub_type_id_3728aada_fk_event_vio FOREIGN KEY (violence_sub_type_id) REFERENCES public.event_violencesubtype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_eventcode event_eventcode_country_id_470322b0_fk_country_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_eventcode
    ADD CONSTRAINT event_eventcode_country_id_470322b0_fk_country_country_id FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_eventcode event_eventcode_event_id_1c5a1c2e_fk_event_event_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_eventcode
    ADD CONSTRAINT event_eventcode_event_id_1c5a1c2e_fk_event_event_id FOREIGN KEY (event_id) REFERENCES public.event_event(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_othersubtype event_othersubtype_created_by_id_78a132e6_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_othersubtype
    ADD CONSTRAINT event_othersubtype_created_by_id_78a132e6_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_othersubtype event_othersubtype_last_modified_by_id_21a4d5c0_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_othersubtype
    ADD CONSTRAINT event_othersubtype_last_modified_by_id_21a4d5c0_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: event_violencesubtype event_violencesubtype_violence_id_b86cfa6b_fk_event_violence_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_violencesubtype
    ADD CONSTRAINT event_violencesubtype_violence_id_b86cfa6b_fk_event_violence_id FOREIGN KEY (violence_id) REFERENCES public.event_violence(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_context_of_violence extraction_extractio_contextofviolence_id_c88afe97_fk_event_con; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_context_of_violence
    ADD CONSTRAINT extraction_extractio_contextofviolence_id_c88afe97_fk_event_con FOREIGN KEY (contextofviolence_id) REFERENCES public.event_contextofviolence(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_countries extraction_extractio_country_id_de831d1b_fk_country_c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_countries
    ADD CONSTRAINT extraction_extractio_country_id_de831d1b_fk_country_c FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_regions extraction_extractio_countryregion_id_e4823cac_fk_country_c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_regions
    ADD CONSTRAINT extraction_extractio_countryregion_id_e4823cac_fk_country_c FOREIGN KEY (countryregion_id) REFERENCES public.country_countryregion(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery extraction_extractio_created_by_id_40650114_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery
    ADD CONSTRAINT extraction_extractio_created_by_id_40650114_fk_users_use FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_crises extraction_extractio_crisis_id_5c5d0015_fk_crisis_cr; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_crises
    ADD CONSTRAINT extraction_extractio_crisis_id_5c5d0015_fk_crisis_cr FOREIGN KEY (crisis_id) REFERENCES public.crisis_crisis(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_disaster_categories extraction_extractio_disastercategory_id_705e8f6e_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_categories
    ADD CONSTRAINT extraction_extractio_disastercategory_id_705e8f6e_fk_event_dis FOREIGN KEY (disastercategory_id) REFERENCES public.event_disastercategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_disaster_sub_categf349 extraction_extractio_disastersubcategory__e40bbbae_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_sub_categf349
    ADD CONSTRAINT extraction_extractio_disastersubcategory__e40bbbae_fk_event_dis FOREIGN KEY (disastersubcategory_id) REFERENCES public.event_disastersubcategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_disaster_sub_types extraction_extractio_disastersubtype_id_0f9e157b_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_sub_types
    ADD CONSTRAINT extraction_extractio_disastersubtype_id_0f9e157b_fk_event_dis FOREIGN KEY (disastersubtype_id) REFERENCES public.event_disastersubtype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_disaster_types extraction_extractio_disastertype_id_8d393a52_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_types
    ADD CONSTRAINT extraction_extractio_disastertype_id_8d393a52_fk_event_dis FOREIGN KEY (disastertype_id) REFERENCES public.event_disastertype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_events extraction_extractio_event_id_65d93e6f_fk_event_eve; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_events
    ADD CONSTRAINT extraction_extractio_event_id_65d93e6f_fk_event_eve FOREIGN KEY (event_id) REFERENCES public.event_event(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_context_of_violence extraction_extractio_extractionquery_id_0fa99430_fk_extractio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_context_of_violence
    ADD CONSTRAINT extraction_extractio_extractionquery_id_0fa99430_fk_extractio FOREIGN KEY (extractionquery_id) REFERENCES public.extraction_extractionquery(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_events extraction_extractio_extractionquery_id_133a29f0_fk_extractio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_events
    ADD CONSTRAINT extraction_extractio_extractionquery_id_133a29f0_fk_extractio FOREIGN KEY (extractionquery_id) REFERENCES public.extraction_extractionquery(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_created_by extraction_extractio_extractionquery_id_1840551b_fk_extractio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_created_by
    ADD CONSTRAINT extraction_extractio_extractionquery_id_1840551b_fk_extractio FOREIGN KEY (extractionquery_id) REFERENCES public.extraction_extractionquery(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_disaster_types extraction_extractio_extractionquery_id_1a2b13f0_fk_extractio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_types
    ADD CONSTRAINT extraction_extractio_extractionquery_id_1a2b13f0_fk_extractio FOREIGN KEY (extractionquery_id) REFERENCES public.extraction_extractionquery(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_countries extraction_extractio_extractionquery_id_1c714003_fk_extractio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_countries
    ADD CONSTRAINT extraction_extractio_extractionquery_id_1c714003_fk_extractio FOREIGN KEY (extractionquery_id) REFERENCES public.extraction_extractionquery(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_disaster_categories extraction_extractio_extractionquery_id_2d0e8e22_fk_extractio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_categories
    ADD CONSTRAINT extraction_extractio_extractionquery_id_2d0e8e22_fk_extractio FOREIGN KEY (extractionquery_id) REFERENCES public.extraction_extractionquery(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_tags extraction_extractio_extractionquery_id_339f830a_fk_extractio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_tags
    ADD CONSTRAINT extraction_extractio_extractionquery_id_339f830a_fk_extractio FOREIGN KEY (extractionquery_id) REFERENCES public.extraction_extractionquery(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_regions extraction_extractio_extractionquery_id_4cdab64e_fk_extractio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_regions
    ADD CONSTRAINT extraction_extractio_extractionquery_id_4cdab64e_fk_extractio FOREIGN KEY (extractionquery_id) REFERENCES public.extraction_extractionquery(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_violence_types extraction_extractio_extractionquery_id_610db1c7_fk_extractio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_violence_types
    ADD CONSTRAINT extraction_extractio_extractionquery_id_610db1c7_fk_extractio FOREIGN KEY (extractionquery_id) REFERENCES public.extraction_extractionquery(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_violence_sub_types extraction_extractio_extractionquery_id_80a391bd_fk_extractio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_violence_sub_types
    ADD CONSTRAINT extraction_extractio_extractionquery_id_80a391bd_fk_extractio FOREIGN KEY (extractionquery_id) REFERENCES public.extraction_extractionquery(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_crises extraction_extractio_extractionquery_id_8114cb87_fk_extractio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_crises
    ADD CONSTRAINT extraction_extractio_extractionquery_id_8114cb87_fk_extractio FOREIGN KEY (extractionquery_id) REFERENCES public.extraction_extractionquery(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_disaster_sub_categf349 extraction_extractio_extractionquery_id_8c281ae5_fk_extractio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_sub_categf349
    ADD CONSTRAINT extraction_extractio_extractionquery_id_8c281ae5_fk_extractio FOREIGN KEY (extractionquery_id) REFERENCES public.extraction_extractionquery(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_sources extraction_extractio_extractionquery_id_94583074_fk_extractio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_sources
    ADD CONSTRAINT extraction_extractio_extractionquery_id_94583074_fk_extractio FOREIGN KEY (extractionquery_id) REFERENCES public.extraction_extractionquery(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_entry_publishers extraction_extractio_extractionquery_id_c42d6079_fk_extractio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_entry_publishers
    ADD CONSTRAINT extraction_extractio_extractionquery_id_c42d6079_fk_extractio FOREIGN KEY (extractionquery_id) REFERENCES public.extraction_extractionquery(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_disaster_sub_types extraction_extractio_extractionquery_id_e6f4ebc4_fk_extractio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_disaster_sub_types
    ADD CONSTRAINT extraction_extractio_extractionquery_id_e6f4ebc4_fk_extractio FOREIGN KEY (extractionquery_id) REFERENCES public.extraction_extractionquery(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_geographical_groups extraction_extractio_extractionquery_id_f18c8c33_fk_extractio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_geographical_groups
    ADD CONSTRAINT extraction_extractio_extractionquery_id_f18c8c33_fk_extractio FOREIGN KEY (extractionquery_id) REFERENCES public.extraction_extractionquery(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_tags extraction_extractio_figuretag_id_a58317a2_fk_entry_fig; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_tags
    ADD CONSTRAINT extraction_extractio_figuretag_id_a58317a2_fk_entry_fig FOREIGN KEY (figuretag_id) REFERENCES public.entry_figuretag(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_geographical_groups extraction_extractio_geographicalgroup_id_b4943087_fk_country_g; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_geographical_groups
    ADD CONSTRAINT extraction_extractio_geographicalgroup_id_b4943087_fk_country_g FOREIGN KEY (geographicalgroup_id) REFERENCES public.country_geographicalgroup(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery extraction_extractio_last_modified_by_id_123fcd99_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery
    ADD CONSTRAINT extraction_extractio_last_modified_by_id_123fcd99_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_entry_publishers extraction_extractio_organization_id_af782d16_fk_organizat; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_entry_publishers
    ADD CONSTRAINT extraction_extractio_organization_id_af782d16_fk_organizat FOREIGN KEY (organization_id) REFERENCES public.organization_organization(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_sources extraction_extractio_organization_id_f62ecdbf_fk_organizat; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_sources
    ADD CONSTRAINT extraction_extractio_organization_id_f62ecdbf_fk_organizat FOREIGN KEY (organization_id) REFERENCES public.organization_organization(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_created_by extraction_extractio_user_id_6ef3d048_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_created_by
    ADD CONSTRAINT extraction_extractio_user_id_6ef3d048_fk_users_use FOREIGN KEY (user_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_violence_types extraction_extractio_violence_id_80b7e2cd_fk_event_vio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_violence_types
    ADD CONSTRAINT extraction_extractio_violence_id_80b7e2cd_fk_event_vio FOREIGN KEY (violence_id) REFERENCES public.event_violence(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extraction_extractionquery_filter_figure_violence_sub_types extraction_extractio_violencesubtype_id_ffbda7f6_fk_event_vio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_extractionquery_filter_figure_violence_sub_types
    ADD CONSTRAINT extraction_extractio_violencesubtype_id_ffbda7f6_fk_event_vio FOREIGN KEY (violencesubtype_id) REFERENCES public.event_violencesubtype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gidd_conflict gidd_conflict_country_id_65a01812_fk_country_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_conflict
    ADD CONSTRAINT gidd_conflict_country_id_65a01812_fk_country_country_id FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gidd_disaster gidd_disaster_country_id_6a74f1f0_fk_country_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_disaster
    ADD CONSTRAINT gidd_disaster_country_id_6a74f1f0_fk_country_country_id FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gidd_disaster gidd_disaster_event_id_be43faf5_fk_event_event_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_disaster
    ADD CONSTRAINT gidd_disaster_event_id_be43faf5_fk_event_event_id FOREIGN KEY (event_id) REFERENCES public.event_event(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gidd_disaster gidd_disaster_hazard_category_id_70ee3fdf_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_disaster
    ADD CONSTRAINT gidd_disaster_hazard_category_id_70ee3fdf_fk_event_dis FOREIGN KEY (hazard_category_id) REFERENCES public.event_disastercategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gidd_disaster gidd_disaster_hazard_sub_category__a907383b_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_disaster
    ADD CONSTRAINT gidd_disaster_hazard_sub_category__a907383b_fk_event_dis FOREIGN KEY (hazard_sub_category_id) REFERENCES public.event_disastersubcategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gidd_disaster gidd_disaster_hazard_sub_type_id_fce81d1d_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_disaster
    ADD CONSTRAINT gidd_disaster_hazard_sub_type_id_fce81d1d_fk_event_dis FOREIGN KEY (hazard_sub_type_id) REFERENCES public.event_disastersubtype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gidd_disaster gidd_disaster_hazard_type_id_998ef3d6_fk_event_disastertype_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_disaster
    ADD CONSTRAINT gidd_disaster_hazard_type_id_998ef3d6_fk_event_disastertype_id FOREIGN KEY (hazard_type_id) REFERENCES public.event_disastertype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gidd_disasterlegacy gidd_disasterlegacy_hazard_category_id_9ae617a6_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_disasterlegacy
    ADD CONSTRAINT gidd_disasterlegacy_hazard_category_id_9ae617a6_fk_event_dis FOREIGN KEY (hazard_category_id) REFERENCES public.event_disastercategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gidd_disasterlegacy gidd_disasterlegacy_hazard_sub_category__46fbef2d_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_disasterlegacy
    ADD CONSTRAINT gidd_disasterlegacy_hazard_sub_category__46fbef2d_fk_event_dis FOREIGN KEY (hazard_sub_category_id) REFERENCES public.event_disastersubcategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gidd_disasterlegacy gidd_disasterlegacy_hazard_sub_type_id_58ae98d0_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_disasterlegacy
    ADD CONSTRAINT gidd_disasterlegacy_hazard_sub_type_id_58ae98d0_fk_event_dis FOREIGN KEY (hazard_sub_type_id) REFERENCES public.event_disastersubtype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gidd_disasterlegacy gidd_disasterlegacy_hazard_type_id_8428ff53_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_disasterlegacy
    ADD CONSTRAINT gidd_disasterlegacy_hazard_type_id_8428ff53_fk_event_dis FOREIGN KEY (hazard_type_id) REFERENCES public.event_disastertype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gidd_displacementdata gidd_displacementdata_country_id_7b9790cf_fk_country_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_displacementdata
    ADD CONSTRAINT gidd_displacementdata_country_id_7b9790cf_fk_country_country_id FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gidd_idpssaddestimate gidd_idpssaddestimate_country_id_1b434d54_fk_country_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_idpssaddestimate
    ADD CONSTRAINT gidd_idpssaddestimate_country_id_1b434d54_fk_country_country_id FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gidd_publicfigureanalysis gidd_publicfigureana_report_id_5097170f_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_publicfigureanalysis
    ADD CONSTRAINT gidd_publicfigureana_report_id_5097170f_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gidd_releasemetadata gidd_releasemetadata_modified_by_id_a8ea52b0_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_releasemetadata
    ADD CONSTRAINT gidd_releasemetadata_modified_by_id_a8ea52b0_fk_users_user_id FOREIGN KEY (modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gidd_statuslog gidd_statuslog_triggered_by_id_d31d5e7b_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gidd_statuslog
    ADD CONSTRAINT gidd_statuslog_triggered_by_id_d31d5e7b_fk_users_user_id FOREIGN KEY (triggered_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: organization_organization_countries organization_organiz_country_id_f59fb399_fk_country_c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_organization_countries
    ADD CONSTRAINT organization_organiz_country_id_f59fb399_fk_country_c FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: organization_organization organization_organiz_created_by_id_6558d3a2_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_organization
    ADD CONSTRAINT organization_organiz_created_by_id_6558d3a2_fk_users_use FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: organization_organizationkind organization_organiz_created_by_id_c4590cd9_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_organizationkind
    ADD CONSTRAINT organization_organiz_created_by_id_c4590cd9_fk_users_use FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: organization_organizationkind organization_organiz_last_modified_by_id_9bdedef2_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_organizationkind
    ADD CONSTRAINT organization_organiz_last_modified_by_id_9bdedef2_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: organization_organization organization_organiz_last_modified_by_id_f9dff5aa_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_organization
    ADD CONSTRAINT organization_organiz_last_modified_by_id_f9dff5aa_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: organization_organization_countries organization_organiz_organization_id_8753609b_fk_organizat; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_organization_countries
    ADD CONSTRAINT organization_organiz_organization_id_8753609b_fk_organizat FOREIGN KEY (organization_id) REFERENCES public.organization_organization(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: organization_organization organization_organiz_organization_kind_id_b3a467d8_fk_organizat; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_organization
    ADD CONSTRAINT organization_organiz_organization_kind_id_b3a467d8_fk_organizat FOREIGN KEY (organization_kind_id) REFERENCES public.organization_organizationkind(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: organization_organization organization_organiz_parent_id_63fa691e_fk_organizat; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_organization
    ADD CONSTRAINT organization_organiz_parent_id_63fa691e_fk_organizat FOREIGN KEY (parent_id) REFERENCES public.organization_organization(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: parking_lot_parkeditem parking_lot_parkedit_country_id_f5157092_fk_country_c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parking_lot_parkeditem
    ADD CONSTRAINT parking_lot_parkedit_country_id_f5157092_fk_country_c FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: parking_lot_parkeditem parking_lot_parkedit_last_modified_by_id_28887820_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parking_lot_parkeditem
    ADD CONSTRAINT parking_lot_parkedit_last_modified_by_id_28887820_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: parking_lot_parkeditem parking_lot_parkeditem_assigned_to_id_1b60e1f0_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parking_lot_parkeditem
    ADD CONSTRAINT parking_lot_parkeditem_assigned_to_id_1b60e1f0_fk_users_user_id FOREIGN KEY (assigned_to_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: parking_lot_parkeditem parking_lot_parkeditem_created_by_id_e1169da1_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parking_lot_parkeditem
    ADD CONSTRAINT parking_lot_parkeditem_created_by_id_e1169da1_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report report_report_created_by_id_f0c7de2c_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report
    ADD CONSTRAINT report_report_created_by_id_f0c7de2c_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_disaggregation_age report_report_disagg_disaggregatedage_id_416edd6a_fk_entry_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_disaggregation_age
    ADD CONSTRAINT report_report_disagg_disaggregatedage_id_416edd6a_fk_entry_dis FOREIGN KEY (disaggregatedage_id) REFERENCES public.entry_disaggregatedage(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_disaggregation_age report_report_disagg_report_id_f7c6e901_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_disaggregation_age
    ADD CONSTRAINT report_report_disagg_report_id_f7c6e901_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_figures report_report_figures_figure_id_5a86d8cc_fk_entry_figure_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_figures
    ADD CONSTRAINT report_report_figures_figure_id_5a86d8cc_fk_entry_figure_id FOREIGN KEY (figure_id) REFERENCES public.entry_figure(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_figures report_report_figures_report_id_ead0575d_fk_report_report_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_figures
    ADD CONSTRAINT report_report_figures_report_id_ead0575d_fk_report_report_id FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_context_of_violence report_report_filter_contextofviolence_id_c86f10d8_fk_event_con; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_context_of_violence
    ADD CONSTRAINT report_report_filter_contextofviolence_id_c86f10d8_fk_event_con FOREIGN KEY (contextofviolence_id) REFERENCES public.event_contextofviolence(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_countries report_report_filter_country_id_914fddfc_fk_country_c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_countries
    ADD CONSTRAINT report_report_filter_country_id_914fddfc_fk_country_c FOREIGN KEY (country_id) REFERENCES public.country_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_regions report_report_filter_countryregion_id_3fc19177_fk_country_c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_regions
    ADD CONSTRAINT report_report_filter_countryregion_id_3fc19177_fk_country_c FOREIGN KEY (countryregion_id) REFERENCES public.country_countryregion(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_crises report_report_filter_crisis_id_6f38a5b7_fk_crisis_cr; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_crises
    ADD CONSTRAINT report_report_filter_crisis_id_6f38a5b7_fk_crisis_cr FOREIGN KEY (crisis_id) REFERENCES public.crisis_crisis(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_disaster_categories report_report_filter_disastercategory_id_02ee6bf8_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_categories
    ADD CONSTRAINT report_report_filter_disastercategory_id_02ee6bf8_fk_event_dis FOREIGN KEY (disastercategory_id) REFERENCES public.event_disastercategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_disaster_sub_categories report_report_filter_disastersubcategory__b365fbd0_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_sub_categories
    ADD CONSTRAINT report_report_filter_disastersubcategory__b365fbd0_fk_event_dis FOREIGN KEY (disastersubcategory_id) REFERENCES public.event_disastersubcategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_disaster_sub_types report_report_filter_disastersubtype_id_82177e07_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_sub_types
    ADD CONSTRAINT report_report_filter_disastersubtype_id_82177e07_fk_event_dis FOREIGN KEY (disastersubtype_id) REFERENCES public.event_disastersubtype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_disaster_types report_report_filter_disastertype_id_0638bc01_fk_event_dis; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_types
    ADD CONSTRAINT report_report_filter_disastertype_id_0638bc01_fk_event_dis FOREIGN KEY (disastertype_id) REFERENCES public.event_disastertype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_events report_report_filter_events_event_id_c2698b6d_fk_event_event_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_events
    ADD CONSTRAINT report_report_filter_events_event_id_c2698b6d_fk_event_event_id FOREIGN KEY (event_id) REFERENCES public.event_event(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_tags report_report_filter_figuretag_id_d7fc29b9_fk_entry_fig; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_tags
    ADD CONSTRAINT report_report_filter_figuretag_id_d7fc29b9_fk_entry_fig FOREIGN KEY (figuretag_id) REFERENCES public.entry_figuretag(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_geographical_groups report_report_filter_geographicalgroup_id_5e8a70dd_fk_country_g; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_geographical_groups
    ADD CONSTRAINT report_report_filter_geographicalgroup_id_5e8a70dd_fk_country_g FOREIGN KEY (geographicalgroup_id) REFERENCES public.country_geographicalgroup(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_entry_publishers report_report_filter_organization_id_2f40c38b_fk_organizat; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_entry_publishers
    ADD CONSTRAINT report_report_filter_organization_id_2f40c38b_fk_organizat FOREIGN KEY (organization_id) REFERENCES public.organization_organization(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_sources report_report_filter_organization_id_e5400c30_fk_organizat; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_sources
    ADD CONSTRAINT report_report_filter_organization_id_e5400c30_fk_organizat FOREIGN KEY (organization_id) REFERENCES public.organization_organization(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_disaster_categories report_report_filter_report_id_03e7abfa_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_categories
    ADD CONSTRAINT report_report_filter_report_id_03e7abfa_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_crises report_report_filter_report_id_06d4595a_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_crises
    ADD CONSTRAINT report_report_filter_report_id_06d4595a_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_created_by report_report_filter_report_id_0f4a4738_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_created_by
    ADD CONSTRAINT report_report_filter_report_id_0f4a4738_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_entry_publishers report_report_filter_report_id_1df6929c_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_entry_publishers
    ADD CONSTRAINT report_report_filter_report_id_1df6929c_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_context_of_violence report_report_filter_report_id_1f746647_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_context_of_violence
    ADD CONSTRAINT report_report_filter_report_id_1f746647_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_sources report_report_filter_report_id_48d866ca_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_sources
    ADD CONSTRAINT report_report_filter_report_id_48d866ca_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_events report_report_filter_report_id_69ef966a_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_events
    ADD CONSTRAINT report_report_filter_report_id_69ef966a_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_violence_sub_types report_report_filter_report_id_8559b2cd_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_violence_sub_types
    ADD CONSTRAINT report_report_filter_report_id_8559b2cd_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_violence_types report_report_filter_report_id_86b06e01_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_violence_types
    ADD CONSTRAINT report_report_filter_report_id_86b06e01_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_tags report_report_filter_report_id_86c5cb7c_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_tags
    ADD CONSTRAINT report_report_filter_report_id_86c5cb7c_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_disaster_sub_types report_report_filter_report_id_86c63b32_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_sub_types
    ADD CONSTRAINT report_report_filter_report_id_86c63b32_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_disaster_types report_report_filter_report_id_87c29dd1_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_types
    ADD CONSTRAINT report_report_filter_report_id_87c29dd1_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_disaster_sub_categories report_report_filter_report_id_bd4ecf07_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_disaster_sub_categories
    ADD CONSTRAINT report_report_filter_report_id_bd4ecf07_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_regions report_report_filter_report_id_bf08d5ab_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_regions
    ADD CONSTRAINT report_report_filter_report_id_bf08d5ab_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_geographical_groups report_report_filter_report_id_c000ab57_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_geographical_groups
    ADD CONSTRAINT report_report_filter_report_id_c000ab57_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_countries report_report_filter_report_id_c69fbb8e_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_countries
    ADD CONSTRAINT report_report_filter_report_id_c69fbb8e_fk_report_re FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_created_by report_report_filter_user_id_63fdd890_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_created_by
    ADD CONSTRAINT report_report_filter_user_id_63fdd890_fk_users_use FOREIGN KEY (user_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_violence_types report_report_filter_violence_id_44de2736_fk_event_vio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_violence_types
    ADD CONSTRAINT report_report_filter_violence_id_44de2736_fk_event_vio FOREIGN KEY (violence_id) REFERENCES public.event_violence(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_filter_figure_violence_sub_types report_report_filter_violencesubtype_id_bcbf94ab_fk_event_vio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_filter_figure_violence_sub_types
    ADD CONSTRAINT report_report_filter_violencesubtype_id_bcbf94ab_fk_event_vio FOREIGN KEY (violencesubtype_id) REFERENCES public.event_violencesubtype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report report_report_is_signed_off_by_id_24155508_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report
    ADD CONSTRAINT report_report_is_signed_off_by_id_24155508_fk_users_user_id FOREIGN KEY (is_signed_off_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report report_report_last_modified_by_id_e7fb27cd_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report
    ADD CONSTRAINT report_report_last_modified_by_id_e7fb27cd_fk_users_user_id FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_reports report_report_report_from_report_id_e30c2d0f_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_reports
    ADD CONSTRAINT report_report_report_from_report_id_e30c2d0f_fk_report_re FOREIGN KEY (from_report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_report_reports report_report_reports_to_report_id_888f510a_fk_report_report_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_report_reports
    ADD CONSTRAINT report_report_reports_to_report_id_888f510a_fk_report_report_id FOREIGN KEY (to_report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_reportapproval report_reportapprova_generation_id_95786e9d_fk_report_re; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportapproval
    ADD CONSTRAINT report_reportapprova_generation_id_95786e9d_fk_report_re FOREIGN KEY (generation_id) REFERENCES public.report_reportgeneration(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_reportapproval report_reportapprova_last_modified_by_id_a9d9bdb3_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportapproval
    ADD CONSTRAINT report_reportapprova_last_modified_by_id_a9d9bdb3_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_reportapproval report_reportapproval_created_by_id_cf587a18_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportapproval
    ADD CONSTRAINT report_reportapproval_created_by_id_cf587a18_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_reportcomment report_reportcomment_created_by_id_a915a051_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportcomment
    ADD CONSTRAINT report_reportcomment_created_by_id_a915a051_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_reportcomment report_reportcomment_last_modified_by_id_a4dea5c2_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportcomment
    ADD CONSTRAINT report_reportcomment_last_modified_by_id_a4dea5c2_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_reportcomment report_reportcomment_report_id_77794c18_fk_report_report_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportcomment
    ADD CONSTRAINT report_reportcomment_report_id_77794c18_fk_report_report_id FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_reportgeneration report_reportgenerat_is_signed_off_by_id_1f276ab9_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportgeneration
    ADD CONSTRAINT report_reportgenerat_is_signed_off_by_id_1f276ab9_fk_users_use FOREIGN KEY (is_signed_off_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_reportgeneration report_reportgenerat_last_modified_by_id_88cb57c5_fk_users_use; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportgeneration
    ADD CONSTRAINT report_reportgenerat_last_modified_by_id_88cb57c5_fk_users_use FOREIGN KEY (last_modified_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_reportgeneration report_reportgeneration_created_by_id_44f315e6_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportgeneration
    ADD CONSTRAINT report_reportgeneration_created_by_id_44f315e6_fk_users_user_id FOREIGN KEY (created_by_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_reportgeneration report_reportgeneration_report_id_02edd85d_fk_report_report_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_reportgeneration
    ADD CONSTRAINT report_reportgeneration_report_id_02edd85d_fk_report_report_id FOREIGN KEY (report_id) REFERENCES public.report_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: users_user_groups users_user_groups_group_id_9afc8d0e_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_user_groups
    ADD CONSTRAINT users_user_groups_group_id_9afc8d0e_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: users_user_groups users_user_groups_user_id_5f6f5a90_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_user_groups
    ADD CONSTRAINT users_user_groups_user_id_5f6f5a90_fk_users_user_id FOREIGN KEY (user_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: users_user_user_permissions users_user_user_perm_permission_id_0b93982e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_user_user_permissions
    ADD CONSTRAINT users_user_user_perm_permission_id_0b93982e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: users_user_user_permissions users_user_user_permissions_user_id_20aca447_fk_users_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_user_user_permissions
    ADD CONSTRAINT users_user_user_permissions_user_id_20aca447_fk_users_user_id FOREIGN KEY (user_id) REFERENCES public.users_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- PostgreSQL database dump complete
--

