"""Exercise the same packaged PetClinic contract against independent H2 files."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from http.cookiejar import CookieJar
from pathlib import Path
import re
import shutil
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, Request, build_opener


class PreserveRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jar", type=Path)
    parser.add_argument("h2_jar", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--port", type=int, default=18094)
    parser.add_argument("--existing-db", type=Path)
    parser.add_argument("--default-init", action="store_true")
    parser.add_argument("--review-regressions", action="store_true",
                        help="run the focused Jex partial-edit and Accept checks")
    args = parser.parse_args()
    if args.default_init and not args.existing_db:
        parser.error("--default-init requires --existing-db")
    args.directory.mkdir()
    db = "jdbc:h2:file:" + str(args.directory.resolve() / "petclinic")
    opener = build_opener(PreserveRedirect(), HTTPCookieProcessor(CookieJar()))
    root = f"http://127.0.0.1:{args.port}"

    def request(path, fields=None, accept=None):
        data = None if fields is None else urlencode(fields).encode()
        try:
            accept = accept or ("application/json" if path in {"/vets", "/actuator/health"} else "text/html")
            response = opener.open(Request(root + path, data=data, headers={"Accept": accept}), timeout=4)
        except HTTPError as error:
            response = error
        with response:
            return response.code, response.headers, response.read().decode(errors="replace")

    def expect(path, status, marker=None, fields=None, media="text/html", accept=None):
        actual, headers, body = request(path, fields, accept)
        assert actual == status, (path, status, actual, body[:400])
        if marker is not None:
            assert marker in body, (path, marker, body[:400])
        if media is not None:
            assert headers.get("Content-Type", "").startswith(media), (path, headers)
        print(status, path, flush=True)
        return headers

    def start(mode):
        log = (args.directory / f"{mode or 'default'}.log").open("wb")
        init = [] if mode is None else [f"--spring.sql.init.mode={mode}"]
        with log:
            proc = subprocess.Popen(
                ["java", "-jar", str(args.jar.resolve()), f"--server.port={args.port}",
                 "--server.address=127.0.0.1", f"--spring.datasource.url={db}",
                 "--spring.datasource.username=sa", "--spring.datasource.password=", *init], stdout=log, stderr=subprocess.STDOUT
            )
        try:
            for _ in range(160):
                if proc.poll() is not None:
                    break
                try:
                    if request("/")[0] == 200:
                        return proc
                except URLError:
                    pass
                time.sleep(0.25)
            raise RuntimeError((args.directory / f"{mode or 'default'}.log").read_text())
        except BaseException:
            stop(proc)
            raise

    def stop(proc):
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                raise

    def sql(query, expected):
        result = subprocess.check_output(
            ["java", "-cp", str(args.h2_jar.resolve()), "org.h2.tools.Shell", "-url", db,
             "-user", "sa", "-password", "", "-sql", query], text=True
        )
        assert re.search(rf"^{re.escape(expected)}$", result, re.MULTILINE), result
        print(query, "=>", expected, flush=True)

    if args.review_regressions:
        proc = start("always")
        try:
            owner_edit = "/owners/1/edit"
            pet_edit = "/owners/1/pets/1/edit"
            expect(owner_edit, 302, fields={}, media=None)
            expect(owner_edit, 302, fields={"city": "New City"}, media=None)
            expect(owner_edit, 200, fields={"firstName": ""})
            expect(pet_edit, 302, fields={"birthDate": "2011-09-07"}, media=None)
            expect(pet_edit, 302, fields={"name": "Leo Edited"}, media=None)
            expect(pet_edit, 200, fields={"name": ""})
            expect("/vets", 200, "dentistry", media="application/xml",
                   accept="application/json;q=0, */*;q=1")
            expect("/vets", 200, "dentistry", media="application/json",
                   accept="application/xml;q=0, application/*;q=1")
            expect("/vets", 200, "dentistry", media="application/xml",
                   accept="application/json;q=0.2, application/xml;q=0.5, application/*;q=1")
            expect("/vets", 406, media=None,
                   accept="application/json;q=0, application/xml;q=0, */*;q=1")
        finally:
            stop(proc)
        sql("select count(*) from owners where id=1 and first_name='George' and last_name='Franklin' "
            "and address='110 W. Liberty St.' and city='New City' and telephone='6085551023'", "1")
        sql("select count(*) from pets where id=1 and owner_id=1 and name='Leo Edited' "
            "and birth_date=date '2011-09-07' and type_id=1", "1")
        return

    if args.existing_db:
        shutil.copyfile(args.existing_db, args.directory / "petclinic.mv.db")
        proc = start(None if args.default_init else "never")
        try:
            location = expect("/owners?lastName=CompositionTrial", 302, media=None)["Location"]
            path = urlsplit(location).path.split(";", 1)[0]
            expect(path, 200, "Trial visit")
            expect(path, 200, "EditedPet")
        finally:
            stop(proc)
        sql("select count(*) from owners where last_name='CompositionTrial' and city='Edited City'", "1")
        return

    owner = dict(firstName="Morgan", lastName="CompositionTrial", address="1 Test Road",
                 city="Test City", telephone="1234567890")
    pet = dict(name="CompositionPet", birthDate="2020-01-02", type="cat")
    proc = start("always")
    try:
        expect("/", 200, "Welcome")
        expect("/owners/find", 200, "Find Owners")
        expect("/owners?page=2", 200, "Owners")
        expect("/owners?page=garbage", 400, media=None)
        expect("/resources/css/petclinic.css", 200, media="text/css")
        expect("/resources/images/pets.png", 200, media="image/png")
        expect("/webjars/font-awesome/css/font-awesome.min.css", 200, media="text/css")
        expect("/webjars/bootstrap/dist/js/bootstrap.bundle.min.js", 200, media=None)
        expect("/actuator/health", 200, '"UP"', media="application/")
        expect("/vets.html", 200, "Veterinarians")
        expect("/vets", 200, "dentistry", media="application/json")
        expect("/vets", 200, "dentistry", media="application/xml", accept="application/xml")
        expect("/oups", 500)
        expect("/owners/new", 200, fields=owner | {"telephone": "invalid"})
        headers = expect("/owners/new", 302, fields=owner, media=None)
        path = urlsplit(headers["Location"]).path.split(";", 1)[0]
        assert re.fullmatch(r"/owners/\d+", path), headers["Location"]
        owner_id = int(path.rsplit("/", 1)[1])
        expect(path, 200, "New Owner Created")
        expect(path + "/edit", 302, fields=owner | {"city": "Edited City", "id": owner_id}, media=None)
        expect(path, 200, "Owner Values Updated")
        expect(path + "/pets/new", 200, fields=pet | {"birthDate": "2099-01-01"})
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _: request(path + "/pets/new", pet), range(2)))
        assert sorted(r[0] for r in results) == [200, 302], results
        assert any("is already in use" in r[2] for r in results if r[0] == 200)
        print("concurrent duplicate pet posts => one redirect, one field error", flush=True)
        details = request(path)[2]
        pet_id = int(re.search(rf"{owner_id}/pets/(\d+)/edit", details).group(1))
        visit = f"{path}/pets/{pet_id}/visits/new"
        future = (date.today() + timedelta(days=7)).isoformat()
        expect(visit, 200, fields={"date": future, "description": ""})
        expect(visit, 200, fields={"date": "2020-01-01", "description": "Past visit"})
        expect(visit, 302, fields={"date": future, "description": "Trial visit + follow-up"}, media=None)
        expect(f"{path}/pets/{pet_id}/edit", 302, fields=pet | {"name": "EditedPet"}, media=None)
        expect(path, 200, "Trial visit")
    finally:
        stop(proc)

    sql("select count(*) from owners where last_name='CompositionTrial' and city='Edited City'", "1")
    sql(f"select count(*) from pets where owner_id={owner_id} and name='EditedPet'", "1")
    sql(f"select count(*) from pets where owner_id={owner_id}", "1")
    sql(f"select count(*) from visits where pet_id={pet_id} and description='Trial visit + follow-up'", "1")
    sql(f"select count(*) from visits where pet_id={pet_id}", "1")

    proc = start("never")
    try:
        expect(path, 200, "Trial visit")
        expect(path, 200, "EditedPet")
    finally:
        stop(proc)


if __name__ == "__main__":
    main()
