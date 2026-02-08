package io.factorialsystems.authorizationservice.repository;

import io.factorialsystems.authorizationservice.model.User;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface UserRepository extends JpaRepository<User, UUID> {

    Optional<User> findByEmail(String email);

    Optional<User> findByOrganizationIdAndEmail(UUID organizationId, String email);

    Page<User> findByOrganizationId(UUID organizationId, Pageable pageable);

    boolean existsByEmail(String email);
}
