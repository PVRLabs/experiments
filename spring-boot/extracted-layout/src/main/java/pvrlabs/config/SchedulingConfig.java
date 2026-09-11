package pvrlabs.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.scheduling.annotation.EnableScheduling;

/** Enables the production GitHub poller while keeping experiment runs scheduler-free. */
@Configuration(proxyBeanMethods = false)
@Profile("!experiment")
@EnableScheduling
public class SchedulingConfig {}
