package experiment;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class Application {
    public static void main(String[] args) { SpringApplication.run(Application.class, args); }
    @GetMapping("/ok") public String ok() { return "ok\n"; }
    @GetMapping("/fail") public ResponseEntity<String> fail() {
        return ResponseEntity.status(500).body("deliberate failure\n");
    }
    @GetMapping("/slow") public String slow() throws InterruptedException {
        Thread.sleep(250);
        return "slow\n";
    }
}
