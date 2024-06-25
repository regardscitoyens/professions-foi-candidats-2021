#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, shutil
import re, time
import csv, json
import requests

HOSTURL = 'https://programme-candidats.interieur.gouv.fr/'
URLS = {
    "DP21": HOSTURL + "elections-departementales-2021/",
    "RG21": HOSTURL + "elections-regionales-2021/",
    "LG22": HOSTURL + "elections-legislatives-2022/",
    "LG24": HOSTURL + "elections-legislatives-2024/"
}


def downloadPDF(eldir, filename, url, retries=3):
    filepath = os.path.join(eldir, "%s.pdf" % filename)
    if os.path.exists(filepath):
        #print >> sys.stderr, "WARNING: already existing PDF", filepath
        return False
    try:
        r = requests.get(url, stream=True)
        r.raw.decode_content = True
        with open(filepath, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
        return True
    except Exception as e:
        if retries:
            time.sleep(2)
            return downloadPDF(eldir, filename, url, retries - 1)
        print >> sys.stderr, "WARNING: could not download %s for" % url, filename
        print >> sys.stderr, "%s:" % type(e), e
        return False


def request_data(url, field, fallback_field=None, retries=10, allow_fail=False):
    jsonurl = "%s.json?_=%s" % (url, time.time())
    #print "CALL %s" % jsonurl
    try:
        jsondata = requests.get(jsonurl).json()
        if field in jsondata:
            return jsondata[field]
        return jsondata[fallback_field]
    except Exception as e:
        if allow_fail:
            print >> sys.stderr, "Data from %s not available yet, skipping it" % jsonurl
            return []
        if retries:
            time.sleep(30/retries)
            return request_data(url, field, fallback_field=fallback_field, retries = retries - 1)
        print >> sys.stderr, "ERROR: impossible to get %s list at" % field, jsonurl
        print >> sys.stderr, "%s:" % type(e), e
        sys.exit(1)


def scrape_regionales_2021(elcode="RG21"):
    eldir = os.path.join("documents", elcode)
    if not os.path.exists(eldir):
        os.makedirs(eldir)
    for tour in [1, 2]:
        nb_reg = 0
        nb_c = 0
        nb_d = 0
        nb_n = 0
        url = URLS[elcode] + "ajax/%s_regions" % tour
        data = {}
        for reg in request_data(url, "data", allow_fail=True):
            nb_reg += 1
            regcode = reg["id"]
            regname = reg["name"]
            regurl = URLS[elcode] + "ajax/%s_listes_rg_%s" % (tour, regcode)
            data[regcode] = {
                "name": regname,
                "url": regurl,
                "listes": request_data(regurl, "data")
            }
            regdir = os.path.join(eldir, regcode)
            if not os.path.exists(regdir):
                os.makedirs(regdir)
            for liste in data[regcode]["listes"]:
                nb_c += 1
                name = ("%s_(%s)" % (liste["nomListe"][:50], liste["nomTeteListe"])).replace(" ", "_")
                codeId = "%s-%s-%s-%s-tour%s-" % (elcode, regcode, name, liste["numPanneau"], tour)
                pdf = liste["pdf_acc"] if liste["pdf_acc"] != "0" else liste["pdf"]
                if pdf != "0":
                    nb_d += 1
                    nb_n += downloadPDF(regdir, codeId + "profession_foi", URLS[elcode] + "data-pdf-propagandes/%s.pdf" % pdf)

        with open(os.path.join(eldir, "%s-tour%s-metadata.json" % (elcode, tour)), "w") as f:
            json.dump(data, f, indent=2)
        if nb_n:
            print "%s tour %s: %s new documents collected (%s total lists are published out of %s listed in %s regions)." % (elcode, tour, nb_n, nb_d, nb_c, nb_reg)


re_extract_familynames = re.compile(r"^(?:M\.|Mme) ([A-Z][A-Z\-\ ]+) .* et (?:M\.|Mme) ([A-Z][A-Z\-\ ]+) .*$")
def scrape_departementales_2021(elcode="DP21"):
    eldir = os.path.join("documents", elcode)
    if not os.path.exists(eldir):
        os.makedirs(eldir)
    for tour in [1, 2]:
        nb_dep = 0
        nb_cantons = 0
        nb_c = 0
        nb_d = 0
        nb_n = 0
        url = URLS[elcode] + "ajax/%s_departements" % tour
        data = {}
        for dept in request_data(url, "data", allow_fail=True):
            nb_dep += 1
            depcode = dept["id"]
            depname = dept["name"]
            depurl = URLS[elcode] + "ajax/%s_cantons_dpt_%s" % (tour, depcode)
            data[depcode] = {
                "name": depname,
                "url": depurl,
                "cantons": {}
            }
            deptdir = os.path.join(eldir, depcode)
            if not os.path.exists(deptdir):
                os.makedirs(deptdir)
            for canton in request_data(depurl, "data"):
                nb_cantons += 1
                cantoncode = canton["codeCanton"]
                cantonname = canton["canton"]
                cantonurl = URLS[elcode] + "ajax/%s_candidats_canton_%s-%s" % (tour, depcode, cantoncode)
                data[depcode]["cantons"][cantoncode] = {
                    "name": cantonname,
                    "url": cantonurl,
                    "candidats": request_data(cantonurl, "data")
                }
                cantondir = os.path.join(deptdir, cantoncode)
                if not os.path.exists(cantondir):
                    os.makedirs(cantondir)
                for candidat in data[depcode]["cantons"][cantoncode]["candidats"]:
                    nb_c += 1
                    name = re_extract_familynames.sub(r"\1+\2", candidat["candidats"]).replace(" ", "_")
                    codeId = "%s-%s-%s-%s-%s-tour%s-" % (elcode, depcode, cantoncode, name, candidat["numPanneau"], tour)
                    pdf = candidat["pdf_acc"] if candidat["pdf_acc"] != "0" else candidat["pdf"]
                    if pdf != "0":
                        nb_d += 1
                        nb_n += downloadPDF(cantondir, codeId + "profession_foi", URLS[elcode] + "data-pdf-propagandes/%s.pdf" % pdf)

        with open(os.path.join(eldir, "%s-tour%s-metadata.json" % (elcode, tour)), "w") as f:
            json.dump(data, f, indent=2)
        if nb_n:
            print "%s tour %s: %s new documents collected (%s total candidates are published out of %s listed in %s departments and %s cantons)." % (elcode, tour, nb_n, nb_d, nb_c, nb_dep, nb_cantons)

def scrape_legislatives(elcode="LG22"):
    eldir = os.path.join("documents", elcode)
    if not os.path.exists(eldir):
        os.makedirs(eldir)
    for tour in [1, 2]:
        nb_dep = 0
        nb_circo = 0
        nb_c = 0
        nb_d = 0
        nb_n = 0
        url = URLS[elcode] + "ajax/%s_departements" % tour
        data = {}
        for dept in request_data(url, "data", allow_fail=True):
            nb_dep += 1
            depcode = dept["id"]
            depname = dept["name"]
            depurl = URLS[elcode] + "ajax/%s_circos_dpt_%s" % (tour, depcode)
            data[depcode] = {
                "name": depname,
                "url": depurl,
                "circonscriptions": {}
            }
            deptdir = os.path.join(eldir, depcode)
            if not os.path.exists(deptdir):
                os.makedirs(deptdir)
            for circo in request_data(depurl, "data", allow_fail=True):
                nb_circo += 1
                circocode = circo["codeDivision"]
                circoname = circo["division"]
                if elcode == "LG22":
                    circourl = URLS[elcode] + "ajax/%s_candidats_circo_%s-%s" % (tour, depcode, circocode)
                else:
                    circourl = URLS[elcode] + "ajax/%s_candidats_circo_%s" % (tour, circocode)
                data[depcode]["circonscriptions"][circocode] = {
                    "name": circoname,
                    "url": circourl,
                    "candidats": request_data(circourl, "data")
                }
                circodir = os.path.join(deptdir, circocode)
                if not os.path.exists(circodir):
                    os.makedirs(circodir)
                for candidat in data[depcode]["circonscriptions"][circocode]["candidats"]:
                    nb_c += 1
                    name = "%s %s" % (candidat["candidatPrenom"], candidat["candidatNom"])
                    codeId = "%s-%s-%s-tour%s-%s-%s-" % (elcode, depcode, circocode, tour, candidat["numPanneau"], name)
                    pdf = candidat["pdf_acc"] if candidat["pdf_acc"] != "0" else candidat["pdf"]
                    if pdf != "0":
                        nb_d += 1
                        nb_n += downloadPDF(circodir, codeId + "profession_foi", URLS[elcode] + "data-pdf-propagandes/%s.pdf" % pdf)
                    pdf_falc = candidat["falc_acc"] if candidat["falc_acc"] != "0" else candidat["falc"]
                    if pdf_falc != "0":
                        downloadPDF(circodir, codeId + "profession_foi_falc", URLS[elcode] + "data-pdf-propagandes/%s.pdf" % pdf_falc)

        with open(os.path.join(eldir, "%s-tour%s-metadata.json" % (elcode, tour)), "w") as f:
            json.dump(data, f, indent=2)
        if nb_n:
            print "%s tour %s: %s new documents collected (%s total candidates are published out of %s listed in %s departments and %s circos)." % (elcode, tour, nb_n, nb_d, nb_c, nb_dep, nb_circo)



if __name__ == '__main__':
    election = ""
    if len(sys.argv) > 1:
        election = sys.argv[1]
    if election == "RG21":
        scrape_regionales_2021()
    elif election == "DP21":
        scrape_departementales_2021()
    elif election.startswith("LG"):
        scrape_legislatives(election)
