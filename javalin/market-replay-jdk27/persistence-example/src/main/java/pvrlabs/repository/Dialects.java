package pvrlabs.repository;

/** SQL selection keys only; a constant does not imply driver or database validation. */
public enum Dialects {
    POSTGRES,
    MYSQL,
    MARIADB,
    SQLITE,
    H2,
    ORACLE,
    SQLSERVER,
    DB2
}
