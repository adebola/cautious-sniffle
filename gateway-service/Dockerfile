FROM eclipse-temurin:21-jdk-alpine AS build
WORKDIR /app

# Copy parent POM first for dependency caching
COPY pom.xml ./pom.xml
COPY .mvn .mvn
COPY mvnw mvnw
RUN chmod +x mvnw

# Copy service POM
COPY gateway-service/pom.xml gateway-service/pom.xml

# Download dependencies (cache layer)
RUN ./mvnw dependency:go-offline -pl gateway-service -am -B

# Copy service source
COPY gateway-service/src gateway-service/src

# Build
RUN ./mvnw package -pl gateway-service -am -DskipTests -B

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

COPY --from=build /app/gateway-service/target/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
