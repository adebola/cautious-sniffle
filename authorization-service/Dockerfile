FROM eclipse-temurin:21-jdk-alpine AS build
WORKDIR /app

# Copy parent POM first for dependency caching
COPY pom.xml ./pom.xml
COPY .mvn .mvn
COPY mvnw mvnw
RUN chmod +x mvnw

# Copy service POM
COPY authorization-service/pom.xml authorization-service/pom.xml

# Download dependencies (cache layer)
RUN ./mvnw dependency:go-offline -pl authorization-service -am -B

# Copy service source
COPY authorization-service/src authorization-service/src

# Build
RUN ./mvnw package -pl authorization-service -am -DskipTests -B

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

COPY --from=build /app/authorization-service/target/*.jar app.jar

EXPOSE 8081

ENTRYPOINT ["java", "-jar", "app.jar"]
