package org.springframework.samples.petclinic.service;

import org.junit.jupiter.api.Test;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.samples.petclinic.owner.Owner;
import org.springframework.samples.petclinic.owner.OwnerRepository;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@SpringBootTest
class BaselineRollbackTests {

	@Autowired
	private OwnerRepository owners;

	@Autowired
	private JdbcTemplate jdbc;

	@Autowired
	private PlatformTransactionManager transactionManager;

	@Test
	void rollsBackFlushedInsertAndAcceptsARecoveryWrite() {
		var transaction = new TransactionTemplate(transactionManager);
		assertThatThrownBy(() -> transaction.executeWithoutResult(status -> {
			owners.saveAndFlush(owner());
			assertThat(count()).isEqualTo(1);
			throw new IllegalStateException("force rollback");
		})).isInstanceOf(IllegalStateException.class).hasMessage("force rollback");
		assertThat(count()).isZero();

		var recovered = owners.saveAndFlush(owner());
		assertThat(recovered.getId()).isNotNull();
		assertThat(count()).isEqualTo(1);
	}

	private int count() {
		return jdbc.queryForObject("select count(*) from owners where last_name='TransactionProbe'", Integer.class);
	}

	private Owner owner() {
		var owner = new Owner();
		owner.setFirstName("Test");
		owner.setLastName("TransactionProbe");
		owner.setAddress("1 Test Street");
		owner.setCity("Test City");
		owner.setTelephone("1234567890");
		return owner;
	}

}
