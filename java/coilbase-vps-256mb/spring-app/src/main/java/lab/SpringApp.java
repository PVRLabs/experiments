package lab;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
@SpringBootApplication
public class SpringApp {
    @Bean static Quotes quotes(HikariDataSource ds) throws Exception { return new Quotes(ds); }
    public static void main(String[] args) { SpringApplication.run(SpringApp.class,args); }
}
